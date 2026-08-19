"""R4.3 Resource -> ProjectResource -> TaskAssignment -> Time enterprise
capacity upgrade -- targeted backend coverage (see docs §43/§80).

Covers: ProjectResource optimistic concurrency, the centralized envelope
policy, the ProjectResourceUsageFact reconciliation reader, Resource.is_active
enforcement at assignment creation, the dead bridge-path removal, and
project-scoped time authorization.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.core.modules.project_management.api.desktop.projects.commands.resource_commands import (
    ProjectResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.projects.factories.projects_api_factory import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.api.desktop.resources.factories.resources_api_factory import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.resource_availability_service import (
    ResourceAvailabilityService,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError
from src.tests.ui_runtime_helpers import login_as


def _setup_project_resource(services, *, planned_hours: float = 40.0):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    project = ps.create_project("Capacity Upgrade Project")
    resource = rs.create_resource("Capacity Upgrade Resource", hourly_rate=70.0)
    project_resource = prs.add_to_project(
        project.id, resource.id, hourly_rate=70.0, currency_code="USD", planned_hours=planned_hours
    )
    task = ts.create_task(project.id, "Capacity Upgrade Task")
    return ps, ts, rs, prs, project, resource, project_resource, task


# ---------------------------------------------------------------------------
# ProjectResource optimistic concurrency
# ---------------------------------------------------------------------------


def test_project_resource_update_with_expected_version_succeeds(services):
    _, _, _, prs, project, resource, project_resource, _ = _setup_project_resource(services)

    prs.update(
        project_resource.id,
        hourly_rate=project_resource.hourly_rate,
        currency_code=project_resource.currency_code,
        planned_hours=Decimal("60"),
        is_active=True,
        expected_version=project_resource.version,
    )

    updated = prs.get(project_resource.id)
    assert updated.planned_hours == Decimal("60")
    assert updated.version == project_resource.version + 1


def test_project_resource_update_stale_version_raises_concurrency_error(services):
    _, _, _, prs, project, resource, project_resource, _ = _setup_project_resource(services)

    prs.update(
        project_resource.id,
        hourly_rate=project_resource.hourly_rate,
        currency_code=project_resource.currency_code,
        planned_hours=Decimal("50"),
        is_active=True,
        expected_version=project_resource.version,
    )

    with pytest.raises(ConcurrencyError) as exc:
        prs.update(
            project_resource.id,
            hourly_rate=project_resource.hourly_rate,
            currency_code=project_resource.currency_code,
            planned_hours=Decimal("55"),
            is_active=True,
            expected_version=project_resource.version,  # now stale
        )
    assert exc.value.code == "STALE_WRITE"


def test_project_resource_update_without_expected_version_still_works(services):
    """Backward compatibility: existing callers that don't pass
    expected_version keep the plain-update behaviour."""
    _, _, _, prs, project, resource, project_resource, _ = _setup_project_resource(services)

    prs.update(
        project_resource.id,
        hourly_rate=project_resource.hourly_rate,
        currency_code=project_resource.currency_code,
        planned_hours=Decimal("45"),
        is_active=True,
    )

    assert prs.get(project_resource.id).planned_hours == Decimal("45")


# ---------------------------------------------------------------------------
# ProjectResourceUsageFact reconciliation reader
# ---------------------------------------------------------------------------


def test_project_resource_usage_reconciles_planned_allocated_actual_remaining(services):
    ps, ts, rs, prs, project, resource, project_resource, task_a = _setup_project_resource(
        services, planned_hours=120.0
    )
    task_b = ts.create_task(project.id, "Capacity Upgrade Task B")
    task_c = ts.create_task(project.id, "Capacity Upgrade Task C")

    assignment_a = ts.assign_project_resource(
        task_id=task_a.id, project_resource_id=project_resource.id, allocation_percent=50.0
    )
    assignment_b = ts.assign_project_resource(
        task_id=task_b.id, project_resource_id=project_resource.id, allocation_percent=30.0
    )
    assignment_c = ts.assign_project_resource(
        task_id=task_c.id, project_resource_id=project_resource.id, allocation_percent=20.0
    )
    ts.update_assignment_planned_hours(
        assignment_a.id, allocated_planned_hours=Decimal("30"),
        expected_assignment_version=assignment_a.version,
        expected_project_resource_version=prs.get(project_resource.id).version,
    )
    ts.update_assignment_planned_hours(
        assignment_b.id, allocated_planned_hours=Decimal("50"),
        expected_assignment_version=assignment_b.version,
        expected_project_resource_version=prs.get(project_resource.id).version,
    )
    ts.update_assignment_planned_hours(
        assignment_c.id, allocated_planned_hours=Decimal("20"),
        expected_assignment_version=assignment_c.version,
        expected_project_resource_version=prs.get(project_resource.id).version,
    )
    ts.add_time_entry(assignment_a.id, entry_date=date(2026, 6, 1), hours=18.0, note="A")
    ts.add_time_entry(assignment_b.id, entry_date=date(2026, 6, 1), hours=42.0, note="B")
    ts.add_time_entry(assignment_c.id, entry_date=date(2026, 6, 1), hours=12.0, note="C")

    usage = prs.get_usage(project_resource.id)

    assert usage.planned_hours == Decimal("120")
    assert usage.allocated_to_tasks_hours == Decimal("100")
    assert usage.unallocated_planned_hours == Decimal("20")
    assert usage.actual_hours == Decimal("72")
    assert usage.remaining_project_hours == Decimal("48")
    assert usage.task_assignment_count == 3
    assert usage.envelope_status == "PARTIALLY_ALLOCATED"
    assert usage.burn_status == "WITHIN_PLAN"


def test_project_resource_usage_is_task_page_independent(services):
    """The rollup must reflect the complete authoritative dataset, not
    whatever page of tasks a caller happens to have loaded."""
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    ts.add_time_entry(assignment.id, entry_date=date(2026, 6, 1), hours=5.0, note="x")

    # Even though nothing about a "current page" is passed here, the usage
    # fact still reflects the complete, authoritative assignment set.
    usage = prs.get_usage(project_resource.id)
    assert usage.actual_hours == Decimal("5")
    assert usage.task_assignment_count == 1


def test_project_resource_usage_not_found_raises(services):
    _, _, _, prs, *_ = _setup_project_resource(services)
    with pytest.raises(NotFoundError):
        prs.get_usage("does-not-exist")


def test_desktop_api_exposes_project_resource_usage_and_version(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(
        services, planned_hours=50.0
    )
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    ts.update_assignment_planned_hours(
        assignment.id, allocated_planned_hours=Decimal("10"),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    api = build_project_management_projects_desktop_api(
        project_service=ps, project_resource_service=prs, resource_service=rs,
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
        project_service=ps, project_resource_service=prs, resource_service=rs,
    )

    api.update_project_resource(
        ProjectResourceUpdateCommand(
            project_resource_id=project_resource.id,
            planned_hours=Decimal("60"),
            is_active=True,
            expected_version=project_resource.version,
        )
    )
    assert prs.get(project_resource.id).planned_hours == Decimal("60")

    with pytest.raises(ConcurrencyError):
        api.update_project_resource(
            ProjectResourceUpdateCommand(
                project_resource_id=project_resource.id,
                planned_hours=Decimal("70"),
                is_active=True,
                expected_version=project_resource.version,  # now stale
            )
        )


# ---------------------------------------------------------------------------
# Overallocation policy: warn (non-blocking) vs strict (blocking) -- neither
# branch had a test proving it actually behaves as configured.
# ---------------------------------------------------------------------------


def _overlapping_overallocation_setup(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    project = ps.create_project("Overallocation Policy Project")
    resource = rs.create_resource("Overallocation Policy Resource", hourly_rate=60.0)
    task_a = ts.create_task(
        project.id, "Overallocation Task A", start_date=date(2026, 7, 6), duration_days=5
    )
    task_b = ts.create_task(
        project.id, "Overallocation Task B", start_date=date(2026, 7, 6), duration_days=5
    )
    # 70% on Task A leaves only 30% of capacity free for the overlapping window.
    ts.assign_resource(task_a.id, resource.id, allocation_percent=70.0)
    return ps, ts, rs, project, resource, task_a, task_b


def test_overallocation_warn_policy_allows_mutation_and_sets_warning(services):
    ts = services["task_service"]
    _, _, _, project, resource, task_a, task_b = _overlapping_overallocation_setup(services)
    assert ts._overallocation_policy == "warn"  # default

    # 80% overlapping Task A's 70% => 150% > 100% capacity -- over the line.
    assignment_b = ts.assign_resource(task_b.id, resource.id, allocation_percent=80.0)

    assert assignment_b is not None
    assert ts._last_overallocation_warning is not None
    assert "over-allocated" in ts._last_overallocation_warning


def test_overallocation_strict_policy_rejects_mutation(services):
    ts = services["task_service"]
    _, _, _, project, resource, task_a, task_b = _overlapping_overallocation_setup(services)
    ts._overallocation_policy = "strict"

    with pytest.raises(BusinessRuleError) as exc:
        ts.assign_resource(task_b.id, resource.id, allocation_percent=80.0)
    assert exc.value.code == "RESOURCE_OVERALLOCATED"

    # The rejected assignment must not have been created.
    remaining = ts.list_assignments_for_task(task_b.id)
    assert remaining == []


def test_overallocation_strict_policy_still_allows_non_conflicting_allocation(services):
    """Strict mode blocks only genuine over-capacity days -- it must not
    become a blanket rejection of every assignment."""
    ts = services["task_service"]
    _, _, _, project, resource, task_a, task_b = _overlapping_overallocation_setup(services)
    ts._overallocation_policy = "strict"

    # 20% overlapping Task A's 70% => 90% <= 100% capacity -- within budget.
    assignment_b = ts.assign_resource(task_b.id, resource.id, allocation_percent=20.0)
    assert assignment_b is not None


# ---------------------------------------------------------------------------
# Resource.is_active enforcement at assignment creation (Defect §37)
# ---------------------------------------------------------------------------


def test_assign_project_resource_rejects_inactive_resource(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    rs.update_resource(resource.id, is_active=False)

    with pytest.raises(BusinessRuleError) as exc:
        ts.assign_project_resource(
            task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
        )
    assert exc.value.code == "RESOURCE_INACTIVE"


# ---------------------------------------------------------------------------
# Deletion / lifecycle guards (Defect §30-32)
# ---------------------------------------------------------------------------


def test_delete_project_resource_with_historical_actuals_is_blocked(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    ts.add_time_entry(assignment.id, entry_date=date(2026, 6, 1), hours=3.0, note="worked")

    with pytest.raises(BusinessRuleError) as exc:
        prs.delete(project_resource.id)
    assert exc.value.code == "PROJECT_RESOURCE_HAS_HISTORICAL_ACTUALS"
    assert prs.get(project_resource.id) is not None


def test_delete_project_resource_without_actuals_still_succeeds(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )

    prs.delete(project_resource.id)

    assert prs.get(project_resource.id) is None


# ---------------------------------------------------------------------------
# Dead bridge path removal (Defect §36)
# ---------------------------------------------------------------------------


def test_assign_resource_bridge_requires_project_resource_repository():
    """The old `if not self._project_resource_repo:` bypass (which allowed
    creating a TaskAssignment with no ProjectResource behind it at all) has
    been removed. A TaskService missing that repo now fails closed rather
    than silently creating an orphaned assignment."""
    from types import SimpleNamespace
    from src.core.modules.project_management.application.tasks.commands.assignment_bridge import (
        TaskAssignmentBridgeMixin,
    )

    class _Bare(TaskAssignmentBridgeMixin):
        _project_resource_repo = None
        _user_session = None

        def _require_manage(self, *args, **kwargs):
            return None

        def _task_repo(self):
            return None

    instance = _Bare()
    instance._task_repo = SimpleNamespace(get=lambda task_id: SimpleNamespace(id=task_id, project_id="proj-1"))
    instance._require_leaf_task = lambda *args, **kwargs: None

    with pytest.raises(BusinessRuleError) as exc:
        instance.assign_resource("task-1", "res-1")
    assert exc.value.code == "PROJECT_RESOURCE_REPO_MISSING"


# ---------------------------------------------------------------------------
# Project-scoped time authorization (Defect §26)
# ---------------------------------------------------------------------------


def test_logging_time_against_task_in_unauthorized_project_is_denied(services):
    auth = services["auth_service"]
    access = services["access_service"]
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project_alpha = ps.create_project("Time Scope Alpha")
    project_beta = ps.create_project("Time Scope Beta")
    task_alpha = ts.create_task(project_alpha.id, "Alpha Task")
    task_beta = ts.create_task(project_beta.id, "Beta Task")
    resource = rs.create_resource("Time Scope Resource", hourly_rate=90.0)
    assignment_alpha = ts.assign_resource(task_alpha.id, resource.id, allocation_percent=50.0)
    assignment_beta = ts.assign_resource(task_beta.id, resource.id, allocation_percent=50.0)

    scoped_user = auth.register_user("time-scoped-manager", "StrongPass123", role_names=["viewer"])
    access.assign_scope_grant(
        scope_type="project",
        scope_id=project_alpha.id,
        user_id=scoped_user.id,
        scope_role="owner",
    )

    login_as(services, "time-scoped-manager", "StrongPass123")

    # Authorized on Alpha: succeeds.
    ts.add_time_entry(assignment_alpha.id, entry_date=date(2026, 6, 2), hours=2.0, note="alpha work")

    # Not authorized on Beta: the global time.manage/task.manage grant from
    # project_alpha's "owner" scope role must not leak into project_beta.
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        ts.add_time_entry(assignment_beta.id, entry_date=date(2026, 6, 2), hours=2.0, note="beta work")


# ---------------------------------------------------------------------------
# Dead capacity/availability wiring -- now real (mid-pass follow-up), and
# migrated onto the calendar-based capacity authority (docs §44).
# ---------------------------------------------------------------------------


def test_resource_multi_project_allocation_service_is_wired_in_composition_root(services):
    """DI-wiring proof: the real (percent-based, multi-project) allocation
    service that backs the Resources workspace's own "Allocation Summary"
    display must be registered under its own key -- previously nothing was
    registered there at all, so that display always reported zero
    conflicts regardless of real data."""
    assert isinstance(
        services.get("resource_multi_project_allocation_service"),
        ResourceAvailabilityService,
    )


def test_enterprise_resource_availability_service_is_wired_into_task_service_for_capacity_authority(
    services,
):
    """DI-wiring proof for the calendar capacity migration (docs §44): the
    SAME EnterpriseResourceAvailabilityService instance registered under
    resource_availability_service must be the one TaskService itself holds
    and uses for `preview_assignment_capacity` -- one shared authority, so
    Task Assignment preview and save-time enforcement cannot disagree by
    construction."""
    ts = services["task_service"]
    availability_service = services["resource_availability_service"]
    assert isinstance(availability_service, EnterpriseResourceAvailabilityService)
    assert ts._enterprise_resource_availability_service is availability_service


def test_assignment_preview_reports_real_overallocation_via_calendar_capacity_authority(
    services,
):
    """Proves the calendar-based capacity migration end to end through the
    Tasks desktop API: preview now comes from `TaskService.
    preview_assignment_capacity` (the same authority save-time enforcement
    uses), not a dead always-zero fallback, and distinguishes existing
    committed capacity from the newly-proposed allocation."""
    window_start = date.today() + timedelta(days=1)

    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Preview Wiring Project")
    resource = rs.create_resource("Preview Wiring Resource", hourly_rate=80.0)
    project_resource = prs.add_to_project(project.id, resource.id, planned_hours=1000.0)
    task_a = ts.create_task(
        project.id, "Preview Task A", start_date=window_start, duration_days=5
    )
    task_c = ts.create_task(
        project.id, "Preview Task C", start_date=window_start, duration_days=5
    )
    task_b = ts.create_task(
        project.id, "Preview Task B", start_date=window_start, duration_days=5
    )
    # 70% + 60% already committed on A and C -> resource is already at 130%
    # of calendar capacity during this window, before Task B is even
    # considered.
    ts.assign_project_resource(
        task_id=task_a.id, project_resource_id=project_resource.id, allocation_percent=70.0
    )
    ts.assign_project_resource(
        task_id=task_c.id, project_resource_id=project_resource.id, allocation_percent=60.0
    )

    api = build_project_management_tasks_desktop_api(
        project_service=ps,
        task_service=ts,
        project_resource_service=prs,
        resource_service=rs,
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
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Availability Display Project")
    resource = rs.create_resource("Availability Display Resource", hourly_rate=65.0)
    # build_resource_availability windows from date.today() forward -- the
    # task must fall inside that window to be picked up.
    task = ts.create_task(
        project.id,
        "Availability Display Task",
        start_date=date.today() + timedelta(days=1),
        duration_days=3,
    )
    ts.assign_resource(task.id, resource.id, allocation_percent=60.0)

    api = build_project_management_resources_desktop_api(
        resource_service=rs,
        availability_service=services["resource_multi_project_allocation_service"],
    )

    availability = api.build_resource_availability(resource.id)
    assert availability is not None
    assert availability.peak_load_percent > 0.0


# ---------------------------------------------------------------------------
# Query-count evidence for the changed N+1 paths (Defect §38/§D)
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


def test_availability_service_task_lookup_issues_one_batch_call_not_one_per_task(services):
    from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
        SqlAlchemyTaskRepository,
    )

    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Availability Query Count Project")
    resource = rs.create_resource("Availability Query Count Resource", hourly_rate=55.0)
    window_start = date.today() + timedelta(days=1)
    for i in range(4):
        task = ts.create_task(
            project.id, f"Availability Task {i}", start_date=window_start, duration_days=2
        )
        ts.assign_resource(task.id, resource.id, allocation_percent=20.0)

    availability_service = services["resource_multi_project_allocation_service"]
    counts, restore = _instrument_get_and_batch(SqlAlchemyTaskRepository, "list_by_ids")
    try:
        availability_service.is_resource_available(
            resource.id, window_start, window_start + timedelta(days=2)
        )
    finally:
        restore()

    assert counts["list_by_ids"] >= 1
    assert counts["get"] == 0
