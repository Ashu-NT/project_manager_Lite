"""ADR-PF-005 cutover — CostPolicyEngine/LaborCostEngine now resolve labor
rates through the rate-card system instead of reading
ProjectResource.hourly_rate/Resource.hourly_rate directly.

See docs/pm_modernization/rate_card_cost_engine_cutover_plan.md for the
approved design this test file verifies.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.common.exceptions import BusinessRuleError


def _labor_actual_rows(snapshot):
    return [
        row
        for row in snapshot.ledger
        if row.source_key == "COMPUTED_LABOR" and row.stage == "actual"
    ]


def test_labor_cost_disagrees_with_legacy_and_project_override_when_rate_card_configured(
    services,
) -> None:
    # Not just parity: Resource.hourly_rate says 50, ProjectResource.hourly_rate
    # says 60, but a project-scoped COST rate-card line says 80 — the cutover
    # result must be 80, proving the new path is authoritative rather than
    # coincidentally agreeing with either legacy source.
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    rate_card_service = services["rate_card_service"]
    finance = services["finance_service"]

    project = ps.create_project("Rate Disagreement", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource(
        "Engineer", role="DEV", hourly_rate=50.0, currency_code="USD"
    )
    pr = prs.add_to_project(
        project_id=project.id,
        resource_id=resource.id,
        planned_hours=5.0,
        hourly_rate=60.0,
        currency_code="USD",
    )
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=pr.id, allocation_percent=100.0
    )
    ts.set_assignment_hours(assignment.id, 2.0)

    card = rate_card_service.create_rate_card(name="Project Override", project_id=project.id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("80"),
        rate_currency="USD",
        resource_id=resource.id,
    )

    snapshot = finance.get_finance_snapshot(project.id, as_of=date.today())
    labor_rows = _labor_actual_rows(snapshot)
    assert sum(row.amount for row in labor_rows) == pytest.approx(160.0)  # 2h x $80


def test_missing_rate_excluded_from_totals_and_recorded_unresolved(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    finance = services["finance_service"]

    project = ps.create_project("Missing Rate", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Unpriced", role="DEV", hourly_rate=0.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 3.0)

    snapshot = finance.get_finance_snapshot(project.id, as_of=date.today())

    assert snapshot.unresolved_labor_rates
    assert any(u.resource_id == resource.id for u in snapshot.unresolved_labor_rates)
    # Excluded from the ledger entirely — never a COMPUTED_LABOR row reading 0.
    assert _labor_actual_rows(snapshot) == []


def test_desktop_dto_reflects_unresolved_labor_rates(services) -> None:
    from src.core.modules.project_management.api.desktop.financials.serializers.snapshot_serializer import (
        serialize_snapshot,
    )

    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    finance = services["finance_service"]

    project = ps.create_project("DTO Incomplete", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Unpriced", role="DEV", hourly_rate=0.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 1.0)

    snapshot = finance.get_finance_snapshot(project.id, as_of=date.today())
    dto = serialize_snapshot(project.id, snapshot)

    assert dto.labor_rates_complete is False
    assert dto.unresolved_labor_rate_count == len(snapshot.unresolved_labor_rates)
    assert dto.unresolved_labor_rate_count >= 1


def test_desktop_dto_reflects_complete_labor_rates(services) -> None:
    from src.core.modules.project_management.api.desktop.financials.serializers.snapshot_serializer import (
        serialize_snapshot,
    )

    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    finance = services["finance_service"]

    project = ps.create_project("DTO Complete", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Priced", role="DEV", hourly_rate=75.0, currency_code="USD")
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 1.0)

    snapshot = finance.get_finance_snapshot(project.id, as_of=date.today())
    dto = serialize_snapshot(project.id, snapshot)

    assert dto.labor_rates_complete is True
    assert dto.unresolved_labor_rate_count == 0


def test_labor_engine_never_uses_billing_rate_type(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    rate_card_service = services["rate_card_service"]
    finance = services["finance_service"]

    project = ps.create_project("Cost Billing Separation", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Unpriced", role="DEV", hourly_rate=0.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 2.0)

    card = rate_card_service.create_rate_card(name="Billing Rates")
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.BILLING,
        unit="HOUR",
        rate_amount=Decimal("150"),
        rate_currency="USD",
        resource_id=resource.id,
    )

    snapshot = finance.get_finance_snapshot(project.id, as_of=date.today())
    # A BILLING-only line must not satisfy the COST-type resolution the
    # labor cost engine performs — still unresolved, not accidentally 150.
    assert snapshot.unresolved_labor_rates
    assert _labor_actual_rows(snapshot) == []


def test_evm_actual_cost_fails_closed_when_labor_rate_unresolved(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project(
        "EVM Incomplete",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=10),
        currency="USD",
    )
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Unpriced", role="DEV", hourly_rate=0.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 2.0)
    baseline = bs.create_baseline(project.id, "BL-Incomplete", rate_as_of=date.today())

    with pytest.raises(BusinessRuleError, match="Actual cost cannot be calculated"):
        rp.get_earned_value(project_id=project.id, baseline_id=baseline.id, as_of=date.today())


def test_actual_cost_total_includes_labor_and_non_labor_when_complete(services) -> None:
    # Regression guard: get_actual_cost/EVM's AC must be the FULL actual
    # cost (labor + non-labor), never narrowed to labor-only.
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cs = services["cost_service"]
    bs = services["baseline_service"]
    rp = services["reporting_service"]

    project = ps.create_project(
        "Full Actual Total",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=10),
        currency="USD",
    )
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Priced", role="DEV", hourly_rate=50.0, currency_code="USD")
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 2.0)  # 100 labor
    cs.add_cost_item(
        project_id=project.id,
        task_id=task.id,
        description="Materials",
        planned_amount=0.0,
        actual_amount=200.0,
        cost_type=CostType.OVERHEAD,
        currency_code="USD",
    )
    baseline = bs.create_baseline(project.id, "BL-Full", rate_as_of=date.today())

    evm = rp.get_earned_value(project_id=project.id, baseline_id=baseline.id, as_of=date.today())
    assert evm.AC == pytest.approx(300.0)  # 100 labor + 200 non-labor


def test_effective_date_selects_correct_rate_card_revision(services) -> None:
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    rate_card_service = services["rate_card_service"]
    finance = services["finance_service"]

    project = ps.create_project("Effective Date Revisions", currency="USD")
    task = ts.create_task(project.id, "Task", start_date=date.today(), duration_days=2)
    resource = rs.create_resource("Unpriced", role="DEV", hourly_rate=0.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    ts.set_assignment_hours(assignment.id, 1.0)

    card = rate_card_service.create_rate_card(name="Revisions")
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("60"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=date.today() - timedelta(days=30),
        effective_to=date.today() - timedelta(days=1),
    )
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("90"),
        rate_currency="USD",
        resource_id=resource.id,
        effective_from=date.today(),
    )

    old_snapshot = finance.get_finance_snapshot(
        project.id, as_of=date.today() - timedelta(days=15)
    )
    new_snapshot = finance.get_finance_snapshot(project.id, as_of=date.today())

    assert sum(row.amount for row in _labor_actual_rows(old_snapshot)) == pytest.approx(60.0)
    assert sum(row.amount for row in _labor_actual_rows(new_snapshot)) == pytest.approx(90.0)
