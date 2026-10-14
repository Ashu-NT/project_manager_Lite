"""Resource -> ProjectResource -> TaskAssignment -> Time enterprise capacity
upgrade -- targeted backend coverage.

Covers: ProjectResource optimistic concurrency, the centralized envelope
policy, the ProjectResourceUsageFact reconciliation reader, Resource.is_active
enforcement at assignment creation, the dead bridge-path removal, and
project-scoped time authorization.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.core.modules.project_management.api.desktop.projects.factories.projects_api_factory import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.api.desktop.resources.factories.resources_api_factory import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.application.projects.dto import (
    ProjectResourceUpdateCommand,
)
from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.modules.project_management.application.resources.capacity.queries.workload import (
    ResourceWorkloadQueryHandler,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
)
from src.tests.ui_runtime_helpers import login_as


def _setup_project_resource(services, *, planned_hours: float = 40.0):
    ps = services['project_query']
    ts = services['task_lookup_query']
    rs = services["resource_query"]
    prs = services["project_resource_query"]
    project = services['project_create'].create_project("Capacity Upgrade Project")
    resource = services["resource_master_commands"].create_resource("Capacity Upgrade Resource", hourly_rate=70.0)
    project_resource = services["project_resource_commands"].add_to_project(
        project.id, resource.id, hourly_rate=70.0, currency_code="USD", planned_hours=planned_hours
    )
    task = services['task_lifecycle_commands'].create_task(project.id, "Capacity Upgrade Task")
    return ps, ts, rs, prs, project, resource, project_resource, task


# ---------------------------------------------------------------------------
# ProjectResource optimistic concurrency
# ---------------------------------------------------------------------------


def test_project_resource_update_with_expected_version_succeeds(services):
    _, _, _, prs, project, resource, project_resource, _ = _setup_project_resource(services)

    services["project_resource_commands"].update(
        project_resource.id,
        hourly_rate=project_resource.hourly_rate,
        currency_code=project_resource.currency_code,
        planned_hours=Decimal(60),
        is_active=True,
        expected_version=project_resource.version,
    )

    updated = prs.get(project_resource.id)
    assert updated.planned_hours == Decimal(60)
    assert updated.version == project_resource.version + 1


def test_project_resource_update_stale_version_raises_concurrency_error(services):
    _, _, _, prs, project, resource, project_resource, _ = _setup_project_resource(services)

    services["project_resource_commands"].update(
        project_resource.id,
        hourly_rate=project_resource.hourly_rate,
        currency_code=project_resource.currency_code,
        planned_hours=Decimal(50),
        is_active=True,
        expected_version=project_resource.version,
    )

    with pytest.raises(ConcurrencyError) as exc:
        services["project_resource_commands"].update(
            project_resource.id,
            hourly_rate=project_resource.hourly_rate,
            currency_code=project_resource.currency_code,
            planned_hours=Decimal(55),
            is_active=True,
            expected_version=project_resource.version,  # now stale
        )
    assert exc.value.code == "STALE_WRITE"


def test_project_resource_update_without_expected_version_still_works(services):
    """Backward compatibility: existing callers that don't pass
    expected_version keep the plain-update behaviour."""
    _, _, _, prs, project, resource, project_resource, _ = _setup_project_resource(services)

    services["project_resource_commands"].update(
        project_resource.id,
        hourly_rate=project_resource.hourly_rate,
        currency_code=project_resource.currency_code,
        planned_hours=Decimal(45),
        is_active=True,
    )

    assert prs.get(project_resource.id).planned_hours == Decimal(45)


# ---------------------------------------------------------------------------
# ProjectResourceUsageFact reconciliation reader
# ---------------------------------------------------------------------------


def test_project_resource_usage_reconciles_planned_allocated_actual_remaining(services):
    ps, ts, rs, prs, project, resource, project_resource, task_a = _setup_project_resource(
        services, planned_hours=120.0
    )
    task_b = services['task_lifecycle_commands'].create_task(project.id, "Capacity Upgrade Task B")
    task_c = services['task_lifecycle_commands'].create_task(project.id, "Capacity Upgrade Task C")

    assignment_a = services['task_assignment_commands'].assign_project_resource(
        task_id=task_a.id, project_resource_id=project_resource.id, allocation_percent=50.0
    )
    assignment_b = services['task_assignment_commands'].assign_project_resource(
        task_id=task_b.id, project_resource_id=project_resource.id, allocation_percent=30.0
    )
    assignment_c = services['task_assignment_commands'].assign_project_resource(
        task_id=task_c.id, project_resource_id=project_resource.id, allocation_percent=20.0
    )
    services['task_assignment_commands'].update_assignment_planned_hours(
        assignment_a.id, allocated_planned_hours=Decimal(30),
        expected_assignment_version=assignment_a.version,
        expected_project_resource_version=prs.get(project_resource.id).version,
    )
    services['task_assignment_commands'].update_assignment_planned_hours(
        assignment_b.id, allocated_planned_hours=Decimal(50),
        expected_assignment_version=assignment_b.version,
        expected_project_resource_version=prs.get(project_resource.id).version,
    )
    services['task_assignment_commands'].update_assignment_planned_hours(
        assignment_c.id, allocated_planned_hours=Decimal(20),
        expected_assignment_version=assignment_c.version,
        expected_project_resource_version=prs.get(project_resource.id).version,
    )
    services["time_entry_commands"].add_time_entry(assignment_a.id, entry_date=date(2026, 6, 1), hours=18.0, note="A")
    services["time_entry_commands"].add_time_entry(assignment_b.id, entry_date=date(2026, 6, 1), hours=42.0, note="B")
    services["time_entry_commands"].add_time_entry(assignment_c.id, entry_date=date(2026, 6, 1), hours=12.0, note="C")

    usage = prs.get_usage(project_resource.id)

    assert usage.planned_hours == Decimal(120)
    assert usage.allocated_to_tasks_hours == Decimal(100)
    assert usage.unallocated_planned_hours == Decimal(20)
    assert usage.actual_hours == Decimal(72)
    assert usage.remaining_project_hours == Decimal(48)
    assert usage.task_assignment_count == 3
    assert usage.envelope_status == "PARTIALLY_ALLOCATED"
    assert usage.burn_status == "WITHIN_PLAN"


def test_project_resource_usage_is_task_page_independent(services):
    """The rollup must reflect the complete authoritative dataset, not
    whatever page of tasks a caller happens to have loaded."""
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    assignment = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    services["time_entry_commands"].add_time_entry(assignment.id, entry_date=date(2026, 6, 1), hours=5.0, note="x")

    # Even though nothing about a "current page" is passed here, the usage
    # fact still reflects the complete, authoritative assignment set.
    usage = prs.get_usage(project_resource.id)
    assert usage.actual_hours == Decimal(5)
    assert usage.task_assignment_count == 1


def test_project_resource_usage_not_found_raises(services):
    _, _, _, prs, *_ = _setup_project_resource(services)
    with pytest.raises(NotFoundError):
        prs.get_usage("does-not-exist")


def test_desktop_api_exposes_project_resource_usage_and_version(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(
        services, planned_hours=50.0
    )
    assignment = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    services['task_assignment_commands'].update_assignment_planned_hours(
        assignment.id, allocated_planned_hours=Decimal(10),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    api = build_project_management_projects_desktop_api(
        project_resource_query=prs, project_resource_commands=services["project_resource_commands"], resource_query=rs,
    )

    dtos = api.list_project_resources(project.id)
    assert dtos[0].version == prs.get(project_resource.id).version

    usage = api.get_project_resource_usage(project_resource.id)
    assert usage.planned_hours_label == "50.0 h"
    assert usage.allocated_to_tasks_hours_label == "10.0 h"
    assert usage.unallocated_planned_hours_label == "40.0 h"
    assert usage.task_assignment_count == 1


def test_desktop_api_update_project_resource_forwards_expected_version_and_conflicts(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    api = build_project_management_projects_desktop_api(
        project_resource_query=prs, project_resource_commands=services["project_resource_commands"], resource_query=rs,
    )

    api.update_project_resource(
        ProjectResourceUpdateCommand(
            project_resource_id=project_resource.id,
            planned_hours=Decimal(60),
            is_active=True,
            expected_version=project_resource.version,
        )
    )
    assert prs.get(project_resource.id).planned_hours == Decimal(60)

    with pytest.raises(ConcurrencyError):
        api.update_project_resource(
            ProjectResourceUpdateCommand(
                project_resource_id=project_resource.id,
                planned_hours=Decimal(70),
                is_active=True,
                expected_version=project_resource.version,  # now stale
            )
        )


# ---------------------------------------------------------------------------
# Overallocation policy: warn (non-blocking) vs strict (blocking) -- neither
# branch had a test proving it actually behaves as configured.
# ---------------------------------------------------------------------------


def _overlapping_overallocation_setup(services):
    ps = services['project_query']
    ts = services['task_lookup_query']
    rs = services["resource_query"]
    project = services['project_create'].create_project("Overallocation Policy Project")
    resource = services["resource_master_commands"].create_resource("Overallocation Policy Resource", hourly_rate=60.0)
    task_a = services['task_lifecycle_commands'].create_task(
        project.id, "Overallocation Task A", start_date=date(2026, 7, 6), duration_days=5
    )
    task_b = services['task_lifecycle_commands'].create_task(
        project.id, "Overallocation Task B", start_date=date(2026, 7, 6), duration_days=5
    )
    # 70% on Task A leaves only 30% of capacity free for the overlapping window.
    services['task_assignment_commands'].assign_resource(task_a.id, resource.id, allocation_percent=70.0)
    return ps, ts, rs, project, resource, task_a, task_b


def test_overallocation_warn_policy_allows_mutation_and_sets_warning(services):
    services['task_lookup_query']
    _, _, _, project, resource, task_a, task_b = _overlapping_overallocation_setup(services)
    assert services['task_assignment_commands']._overallocation_policy == "warn"  # default

    # 80% overlapping Task A's 70% => 150% > 100% capacity -- over the line.
    assignment_b = services['task_assignment_commands'].assign_resource(task_b.id, resource.id, allocation_percent=80.0)

    assert assignment_b is not None
    assert services['task_assignment_commands']._last_overallocation_warning is not None
    assert "over-allocated" in services['task_assignment_commands']._last_overallocation_warning


def test_overallocation_strict_policy_rejects_mutation(services):
    services['task_lookup_query']
    _, _, _, project, resource, task_a, task_b = _overlapping_overallocation_setup(services)
    services['task_assignment_commands']._overallocation_policy = "strict"

    with pytest.raises(BusinessRuleError) as exc:
        services['task_assignment_commands'].assign_resource(task_b.id, resource.id, allocation_percent=80.0)
    assert exc.value.code == "RESOURCE_OVERALLOCATED"

    # The rejected assignment must not have been created.
    remaining = services['task_assignment_commands'].list_assignments_for_task(task_b.id)
    assert remaining == []


def test_overallocation_strict_policy_still_allows_non_conflicting_allocation(services):
    """Strict mode blocks only genuine over-capacity days -- it must not
    become a blanket rejection of every assignment."""
    services['task_lookup_query']
    _, _, _, project, resource, task_a, task_b = _overlapping_overallocation_setup(services)
    services['task_assignment_commands']._overallocation_policy = "strict"

    # 20% overlapping Task A's 70% => 90% <= 100% capacity -- within budget.
    assignment_b = services['task_assignment_commands'].assign_resource(task_b.id, resource.id, allocation_percent=20.0)
    assert assignment_b is not None


# ---------------------------------------------------------------------------
# Resource.is_active enforcement at assignment creation
# ---------------------------------------------------------------------------


def test_assign_project_resource_rejects_inactive_resource(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    services["resource_master_commands"].deactivate_resource(resource_id=resource.id, expected_version=resource.version)

    with pytest.raises(BusinessRuleError) as exc:
        services['task_assignment_commands'].assign_project_resource(
            task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
        )
    assert exc.value.code == "RESOURCE_INACTIVE"


# ---------------------------------------------------------------------------
# Deletion / lifecycle guards
# ---------------------------------------------------------------------------


def test_delete_project_resource_with_historical_actuals_is_blocked(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    assignment = services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    services["time_entry_commands"].add_time_entry(assignment.id, entry_date=date(2026, 6, 1), hours=3.0, note="worked")

    with pytest.raises(BusinessRuleError) as exc:
        services["project_resource_commands"].delete(project_resource.id)
    assert exc.value.code == "PROJECT_RESOURCE_HAS_HISTORICAL_ACTUALS"
    assert prs.get(project_resource.id) is not None


def test_delete_project_resource_without_actuals_still_succeeds(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    services['task_assignment_commands'].assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )

    services["project_resource_commands"].delete(project_resource.id)

    assert prs.get(project_resource.id) is None


# ---------------------------------------------------------------------------
# Dead bridge path removal
# ---------------------------------------------------------------------------


def test_assign_resource_requires_project_resource_repository(services, monkeypatch):
    """A missing envelope repository cannot create an orphaned assignment."""
    project = services['project_create'].create_project("Assignment Repository Guard", "")
    services['task_lookup_query']
    task = services['task_lifecycle_commands'].create_task(project.id, "Work")
    monkeypatch.setattr(services['task_assignment_commands'], "_project_resource_repo", None)

    with pytest.raises(BusinessRuleError) as exc:
        services['task_assignment_commands'].assign_resource(task.id, "res-1")
    assert exc.value.code == "PROJECT_RESOURCE_REPO_MISSING"


# ---------------------------------------------------------------------------
# Project-scoped time authorization
# ---------------------------------------------------------------------------


def test_logging_time_against_task_in_unauthorized_project_is_denied(services):
    access = services["access_service"]
    services['project_query']
    services['task_lookup_query']

    project_alpha = services['project_create'].create_project("Time Scope Alpha")
    project_beta = services['project_create'].create_project("Time Scope Beta")
    task_alpha = services['task_lifecycle_commands'].create_task(project_alpha.id, "Alpha Task")
    task_beta = services['task_lifecycle_commands'].create_task(project_beta.id, "Beta Task")
    resource = services["resource_master_commands"].create_resource("Time Scope Resource", hourly_rate=90.0)
    assignment_alpha = services['task_assignment_commands'].assign_resource(task_alpha.id, resource.id, allocation_percent=50.0)
    assignment_beta = services['task_assignment_commands'].assign_resource(task_beta.id, resource.id, allocation_percent=50.0)

    scoped_user = services["user_registration"].register_user("time-scoped-manager", "StrongPass123", role_names=["viewer"])
    access.assign_scope_grant(
        scope_type="project",
        scope_id=project_alpha.id,
        user_id=scoped_user.id,
        scope_role="owner",
    )

    login_as(services, "time-scoped-manager", "StrongPass123")

    # Authorized on Alpha: succeeds.
    services["time_entry_commands"].add_time_entry(assignment_alpha.id, entry_date=date(2026, 6, 2), hours=2.0, note="alpha work")

    # Not authorized on Beta: the global time.manage/task.manage grant from
    # project_alpha's "owner" scope role must not leak into project_beta.
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        services["time_entry_commands"].add_time_entry(assignment_beta.id, entry_date=date(2026, 6, 2), hours=2.0, note="beta work")


# ---------------------------------------------------------------------------
# Capacity/availability wiring migrated onto the calendar-based capacity authority.
# ---------------------------------------------------------------------------


def test_resource_workload_query_is_wired_in_composition_root(services):
    assert isinstance(services.get("resource_workload_query"), ResourceWorkloadQueryHandler)
    assert "resource_multi_project_allocation_service" not in services


def test_enterprise_resource_availability_service_is_wired_into_task_service_for_capacity_authority(
    services,
):
    """DI-wiring proof for the calendar capacity migration: the SAME
    ResourceAvailabilityQueryHandler instance registered under
    resource_availability_service must be the one TaskService itself holds
    and uses for `preview_assignment_capacity` -- one shared authority, so
    Task Assignment preview and save-time enforcement cannot disagree by
    construction."""
    services['task_lookup_query']
    availability_service = services["resource_availability_service"]
    assert isinstance(availability_service, ResourceAvailabilityQueryHandler)
    assert services['task_assignment_commands']._enterprise_resource_availability_service is availability_service


def test_assignment_preview_reports_real_overallocation_via_calendar_capacity_authority(
    services,
):
    """Proves the calendar-based capacity migration end to end through the
    Tasks desktop API: preview now comes from `TaskService.
    preview_assignment_capacity` (the same authority save-time enforcement
    uses), not a dead always-zero fallback, and distinguishes existing
    committed capacity from the newly-proposed allocation."""
    window_start = date.today() + timedelta(days=1)

    ps = services['project_query']
    services['task_lookup_query']
    rs = services["resource_query"]
    prs = services["project_resource_query"]

    project = services['project_create'].create_project("Preview Wiring Project")
    resource = services["resource_master_commands"].create_resource("Preview Wiring Resource", hourly_rate=80.0)
    project_resource = services["project_resource_commands"].add_to_project(project.id, resource.id, planned_hours=1000.0)
    task_a = services['task_lifecycle_commands'].create_task(
        project.id, "Preview Task A", start_date=window_start, duration_days=5
    )
    task_c = services['task_lifecycle_commands'].create_task(
        project.id, "Preview Task C", start_date=window_start, duration_days=5
    )
    task_b = services['task_lifecycle_commands'].create_task(
        project.id, "Preview Task B", start_date=window_start, duration_days=5
    )
    # 70% + 60% already committed on A and C -> resource is already at 130%
    # of calendar capacity during this window, before Task B is even
    # considered.
    services['task_assignment_commands'].assign_project_resource(
        task_id=task_a.id, project_resource_id=project_resource.id, allocation_percent=70.0
    )
    services['task_assignment_commands'].assign_project_resource(
        task_id=task_c.id, project_resource_id=project_resource.id, allocation_percent=60.0
    )

    api = build_project_management_tasks_desktop_api(
        project_service=ps,
        task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'],
        project_resource_query=prs,
        resource_query=rs,
        assignment_skill_validator=None,
    )

    preview = api.preview_assignment(
        task_b.id, project_resource.id, proposed_allocation_percent=100.0
    )

    assert preview.capacity_known is True
    assert preview.capacity_status == "OVER_CAPACITY"
    assert preview.peak_utilization_percent > 100.0
    assert preview.overallocation_pct > 0.0
    assert preview.conflict_projects == (project.name,)


def test_resource_availability_display_returns_real_data_not_none(services):
    """Resources workspace's capacity display previously always resolved
    to None (and therefore the all-zero "Allocation Summary" fallback in
    QML), because the calendar-based service it was wired to didn't
    implement the method being called on it."""
    services['project_query']
    services['task_lookup_query']
    rs = services["resource_query"]

    project = services['project_create'].create_project("Availability Display Project")
    resource = services["resource_master_commands"].create_resource("Availability Display Resource", hourly_rate=65.0)
    window_start = date.today()
    window_end = window_start + timedelta(days=29)
    task = services['task_lifecycle_commands'].create_task(
        project.id,
        "Availability Display Task",
        start_date=window_start + timedelta(days=1),
        duration_days=3,
    )
    services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=60.0)

    api = build_project_management_resources_desktop_api(
        resource_query=rs,
        workload_service=services["resource_workload_query"],
    )

    availability = api.build_resource_availability(
        resource.id,
        start_date=window_start.isoformat(),
        end_date=window_end.isoformat(),
    )
    assert availability.planned_commitment_hours > 0.0
    assert availability.assignment_count == 1
    assert availability.days


# ---------------------------------------------------------------------------
# Query-count evidence for the changed N+1 paths
# ---------------------------------------------------------------------------


def _instrument_get_and_batch(cls, batch_method_name: str):
    """Wrap get()/<batch_method_name>() on a repository CLASS with call
    counters. Returns (counts, restore) -- mirrors the established pattern
    in test_approved_time_work_allocation_n_plus_one.py."""
    counts = {"get": 0, batch_method_name: 0}
    real_get = cls.get
    real_batch = getattr(cls, batch_method_name)

    def counting_get(self, *args, **kwargs):
        counts["get"] += 1
        return real_get(self, *args, **kwargs)

    def counting_batch(self, *args, **kwargs):
        counts[batch_method_name] += 1
        return real_batch(self, *args, **kwargs)

    cls.get = counting_get
    setattr(cls, batch_method_name, counting_batch)

    def restore():
        cls.get = real_get
        setattr(cls, batch_method_name, real_batch)

    return counts, restore


def test_resource_workload_uses_bounded_reader_not_repository_wide_task_lookup(services):
    from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
        SqlAlchemyAssignmentRepository,
        SqlAlchemyTaskRepository,
    )

    services['project_query']
    services['task_lookup_query']

    project = services['project_create'].create_project("Availability Query Count Project")
    resource = services["resource_master_commands"].create_resource("Availability Query Count Resource", hourly_rate=55.0)
    window_start = date.today() + timedelta(days=1)
    for i in range(4):
        task = services['task_lifecycle_commands'].create_task(
            project.id, f"Availability Task {i}", start_date=window_start, duration_days=2
        )
        services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=20.0)

    workload_service = services["resource_workload_query"]
    task_counts, restore_tasks = _instrument_get_and_batch(
        SqlAlchemyTaskRepository, "list_by_ids"
    )
    assignment_calls = {"list_by_resource": 0}
    real_list_by_resource = SqlAlchemyAssignmentRepository.list_by_resource

    def counting_list_by_resource(self, *args, **kwargs):
        assignment_calls["list_by_resource"] += 1
        return real_list_by_resource(self, *args, **kwargs)

    SqlAlchemyAssignmentRepository.list_by_resource = counting_list_by_resource
    try:
        workload_service.read(
            resource.id,
            start_date=window_start,
            end_date=window_start + timedelta(days=2),
        )
    finally:
        restore_tasks()
        SqlAlchemyAssignmentRepository.list_by_resource = real_list_by_resource

    assert task_counts["list_by_ids"] == 0
    assert task_counts["get"] == 0
    assert assignment_calls["list_by_resource"] == 0
