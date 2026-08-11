from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.modules.project_management.domain.financials.planned_cost import (
    PLANNED_HOURS_FULLY_ALLOCATED,
    PLANNED_HOURS_PARTIALLY_ALLOCATED,
    PlannedCostVersionStatus,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_project(services, *, planned_hours: float = 40.0, hourly_rate: float = 50.0):
    project = services["project_service"].create_project(
        "Planned Cost Project", financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="LABOR-DEFAULT", name="Default Labor"
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id,
        expected_version=profile.version,
        default_cost_code_id=cost_code.id,
    )
    resource = services["resource_service"].create_resource(
        "Engineer One", hourly_rate=hourly_rate, currency_code="USD"
    )
    project_resource = services["project_resource_service"].add_to_project(
        project.id, resource.id, hourly_rate=hourly_rate, currency_code="USD",
        planned_hours=planned_hours,
    )
    task = services["task_service"].create_task(project.id, "Design Task")
    assignment = services["task_service"].assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    return {
        "project": project,
        "cost_code": cost_code,
        "resource": resource,
        "project_resource": project_resource,
        "task": task,
        "assignment": assignment,
    }


def _allocate(services, ctx, hours: Decimal, *, assignment=None, project_resource=None):
    # Mutates the passed-in (or ctx-default) assignment/project_resource
    # objects in place with their post-call versions, so a second
    # `_allocate` call in the same test reads fresh `expected_*_version`
    # values rather than the ones captured at setup time.
    assignment = assignment or ctx["assignment"]
    project_resource = project_resource or ctx["project_resource"]
    updated = services["task_service"].update_assignment_planned_hours(
        assignment.id,
        allocated_planned_hours=hours,
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    assignment.version = updated.version
    assignment.allocated_planned_hours = updated.allocated_planned_hours
    project_resource.version += 1
    return updated


# ---------------------------------------------------------------------------
# Write-time reconciliation (TaskAssignmentMixin.update_assignment_planned_hours)
# ---------------------------------------------------------------------------


def test_allocating_within_envelope_succeeds(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    updated = _allocate(services, ctx, Decimal("30"))
    assert updated.allocated_planned_hours == Decimal("30")
    assert updated.version == 2


def test_allocating_beyond_envelope_is_rejected(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    with pytest.raises(BusinessRuleError) as exc:
        _allocate(services, ctx, Decimal("41"))
    assert exc.value.code == "PROJECT_RESOURCE_HOURS_OVERALLOCATED"


def test_allocating_across_two_tasks_reconciles_against_shared_envelope(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    task2 = services["task_service"].create_task(ctx["project"].id, "Build Task")
    assignment2 = services["task_service"].assign_project_resource(
        task_id=task2.id,
        project_resource_id=ctx["project_resource"].id,
        allocation_percent=50.0,
    )
    _allocate(services, ctx, Decimal("25"))
    # 25 (task 1) + 20 (task 2) = 45 > 40 envelope.
    with pytest.raises(BusinessRuleError) as exc:
        _allocate(services, ctx, Decimal("20"), assignment=assignment2)
    assert exc.value.code == "PROJECT_RESOURCE_HOURS_OVERALLOCATED"
    # 25 + 15 = 40, exactly the envelope — allowed.
    updated = _allocate(services, ctx, Decimal("15"), assignment=assignment2)
    assert updated.allocated_planned_hours == Decimal("15")


def test_shrinking_envelope_below_allocated_total_is_rejected(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    _allocate(services, ctx, Decimal("30"))
    with pytest.raises(BusinessRuleError) as exc:
        services["project_resource_service"].update(
            ctx["project_resource"].id,
            hourly_rate=ctx["project_resource"].hourly_rate,
            currency_code=ctx["project_resource"].currency_code,
            planned_hours=20.0,
            is_active=True,
        )
    assert exc.value.code == "PROJECT_RESOURCE_ENVELOPE_BELOW_ALLOCATIONS"
    # Shrinking to exactly the allocated total is allowed.
    services["project_resource_service"].update(
        ctx["project_resource"].id,
        hourly_rate=ctx["project_resource"].hourly_rate,
        currency_code=ctx["project_resource"].currency_code,
        planned_hours=30.0,
        is_active=True,
    )


def test_stale_assignment_version_raises_concurrency_error(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    _allocate(services, ctx, Decimal("10"))
    with pytest.raises(Exception) as exc:
        services["task_service"].update_assignment_planned_hours(
            ctx["assignment"].id,
            allocated_planned_hours=Decimal("15"),
            expected_assignment_version=1,  # stale — already advanced to 2
            expected_project_resource_version=ctx["project_resource"].version,
        )
    assert getattr(exc.value, "code", None) == "STALE_WRITE"


# ---------------------------------------------------------------------------
# calculate_snapshot
# ---------------------------------------------------------------------------


def test_calculate_snapshot_basic_correctness(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0, hourly_rate=50.0)
    _allocate(services, ctx, Decimal("30"))

    result = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    )
    version = result.version
    assert version.status == PlannedCostVersionStatus.CURRENT
    assert version.revision == 1
    assert version.rates_complete is True
    assert version.allocations_complete is False
    assert version.partially_allocated_resource_count == 1
    assert version.unresolved_rate_count == 0

    lines = services["planned_cost_service"].list_lines(version.id)
    assert len(lines) == 1
    line = lines[0]
    assert line.task_id == ctx["task"].id
    assert line.resource_id == ctx["resource"].id
    assert line.project_resource_id == ctx["project_resource"].id
    assert line.cost_code_id == ctx["cost_code"].id
    assert line.source_assignment_id == ctx["assignment"].id
    assert line.planned_hours == Decimal("30")
    assert line.amount == Decimal("30") * line.rate_amount

    diagnostics = {d.resource_id: d for d in result.diagnostics}
    diag = diagnostics[ctx["resource"].id]
    assert diag.reason_code == PLANNED_HOURS_PARTIALLY_ALLOCATED
    assert diag.envelope_hours == Decimal("40")
    assert diag.allocated_hours == Decimal("30")
    assert diag.unallocated_hours == Decimal("10")


def test_fully_allocated_envelope_marks_allocations_complete(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    _allocate(services, ctx, Decimal("40"))
    result = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    )
    assert result.version.allocations_complete is True
    assert result.version.partially_allocated_resource_count == 0
    diag = result.diagnostics[0]
    assert diag.reason_code == PLANNED_HOURS_FULLY_ALLOCATED
    assert diag.unallocated_hours == Decimal("0")


def test_empty_project_produces_valid_empty_snapshot(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    # No allocation performed — assignment.allocated_planned_hours stays 0.
    result = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    )
    assert result.version.status == PlannedCostVersionStatus.CURRENT
    assert services["planned_cost_service"].list_lines(result.version.id) == []


def test_missing_default_cost_code_fails_closed(services) -> None:
    project = services["project_service"].create_project(
        "No Cost Code Project", financial_currency_code="USD"
    )
    with pytest.raises(BusinessRuleError) as exc:
        services["planned_cost_service"].calculate_snapshot(project.id, calculated_by="admin")
    assert exc.value.code == "PLANNED_COST_NO_DEFAULT_COST_CODE"


def test_calculation_supersedes_previous_version_and_increments_revision(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    _allocate(services, ctx, Decimal("10"))
    first = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    ).version

    _allocate(services, ctx, Decimal("20"))
    second = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    ).version

    assert second.revision == first.revision + 1
    refreshed_first = services["planned_cost_service"].get_version(first.id)
    assert refreshed_first.status == PlannedCostVersionStatus.SUPERSEDED
    assert refreshed_first.superseded_by == "admin"
    current = services["planned_cost_service"].get_current_snapshot(ctx["project"].id)
    assert current.id == second.id


def test_totals_by_task_and_cost_code_match_lines(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    _allocate(services, ctx, Decimal("30"))
    version = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    ).version

    by_task = services["planned_cost_service"].get_totals_by_task(version.id)
    by_cost_code = services["planned_cost_service"].get_totals_by_cost_code(version.id)
    lines = services["planned_cost_service"].list_lines(version.id)
    expected_total = sum((line.amount for line in lines), Decimal("0"))
    assert sum(by_task.values(), Decimal("0")) == expected_total
    assert sum(by_cost_code.values(), Decimal("0")) == expected_total
    assert by_task[ctx["task"].id] == expected_total
    assert by_cost_code[ctx["cost_code"].id] == expected_total


def test_source_assignment_id_survives_assignment_deletion(services) -> None:
    ctx = _setup_project(services, planned_hours=40.0)
    _allocate(services, ctx, Decimal("30"))
    version = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    ).version
    line_before = services["planned_cost_service"].list_lines(version.id)[0]

    services["task_service"].unassign_resource(ctx["assignment"].id)

    line_after = services["planned_cost_service"].list_lines(version.id)[0]
    assert line_after.source_assignment_id == line_before.source_assignment_id
    assert line_after.amount == line_before.amount
    assert line_after.planned_hours == line_before.planned_hours


def test_version_not_found_raises(services) -> None:
    with pytest.raises(NotFoundError):
        services["planned_cost_service"].get_version("does-not-exist")
