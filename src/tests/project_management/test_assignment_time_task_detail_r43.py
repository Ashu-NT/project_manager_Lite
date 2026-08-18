"""R4.3 Task Detail (Assignment + Time) backend upgrade — targeted coverage.

Covers the concrete, evidence-based fixes made during the deep Assignment +
Time audit (see docs §43): optimistic-concurrency on allocation edits,
read-side exposure of allocated_planned_hours/version, the task-scoped (not
resource-wide) Time Summary fix, and removal of the "Set Hours" UI affordance.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.api.desktop.timesheets.builders.assignment_snapshot_builder import (
    build_assignment_snapshot,
)
from src.core.platform.common.exceptions import ConcurrencyError


def _setup_assignment(services, *, allocation_percent: float = 50.0):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    project = ps.create_project("Assignment Concurrency Project")
    task = ts.create_task(project.id, "Concurrency Task")
    resource = rs.create_resource("Concurrency Resource", hourly_rate=90.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=allocation_percent)
    return project, task, resource, assignment


# ---------------------------------------------------------------------------
# set_assignment_allocation — optimistic concurrency (Defect #2)
# ---------------------------------------------------------------------------


def test_set_assignment_allocation_with_expected_version_succeeds_and_increments_version(services):
    ts = services["task_service"]
    _, _, _, assignment = _setup_assignment(services)

    updated = ts.set_assignment_allocation(
        assignment.id, 75.0, expected_version=assignment.version
    )

    assert updated.allocation_percent == 75.0
    assert updated.version == assignment.version + 1


def test_set_assignment_allocation_stale_version_raises_concurrency_error(services):
    ts = services["task_service"]
    _, _, _, assignment = _setup_assignment(services)

    ts.set_assignment_allocation(assignment.id, 60.0, expected_version=assignment.version)

    with pytest.raises(ConcurrencyError) as exc:
        ts.set_assignment_allocation(
            assignment.id, 80.0, expected_version=assignment.version
        )
    assert exc.value.code == "STALE_WRITE"


def test_set_assignment_allocation_without_expected_version_still_works(services):
    """Backward compatibility: callers that don't pass expected_version keep
    the pre-existing plain-update behaviour (no caller should be silently
    broken by adding concurrency protection)."""
    ts = services["task_service"]
    _, _, _, assignment = _setup_assignment(services)

    updated = ts.set_assignment_allocation(assignment.id, 65.0)

    assert updated.allocation_percent == 65.0


# ---------------------------------------------------------------------------
# Desktop API read-side exposure of allocated_planned_hours / version (Defect #1)
# ---------------------------------------------------------------------------


def test_task_assignment_desktop_dto_exposes_planned_hours_and_version(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Planned Hours Exposure Project")
    resource = rs.create_resource("Planned Hours Resource", hourly_rate=80.0)
    project_resource = prs.add_to_project(
        project.id, resource.id, hourly_rate=80.0, currency_code="USD", planned_hours=40.0
    )
    task = ts.create_task(project.id, "Planned Hours Task")
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    ts.update_assignment_planned_hours(
        assignment.id,
        allocated_planned_hours=Decimal("12"),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )

    api = build_project_management_tasks_desktop_api(
        project_service=ps,
        task_service=ts,
        project_resource_service=prs,
        resource_service=rs,
    )
    dtos = api.list_assignments(task.id)
    assert len(dtos) == 1
    assert dtos[0].allocated_planned_hours == "12"
    assert dtos[0].version == 2


# ---------------------------------------------------------------------------
# Time Summary is task-scoped, not resource-wide (Defect #3)
# ---------------------------------------------------------------------------


def test_build_assignment_snapshot_logged_is_task_scoped_not_resource_wide(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Scope Leak Project")
    resource = rs.create_resource("Shared Resource", hourly_rate=70.0)

    task_a = ts.create_task(project.id, "Task A")
    task_b = ts.create_task(project.id, "Task B")
    assignment_a = ts.assign_resource(task_a.id, resource.id, allocation_percent=50.0)
    assignment_b = ts.assign_resource(task_b.id, resource.id, allocation_percent=50.0)

    entry_date = date(2026, 4, 6)
    ts.add_time_entry(assignment_a.id, entry_date=entry_date, hours=2.0, note="Task A work")
    ts.add_time_entry(assignment_b.id, entry_date=entry_date, hours=5.0, note="Task B work")

    snapshot_a = build_assignment_snapshot(
        assignment_a.id,
        period_start=None,
        task_service=ts,
        timesheet_service=services["timesheet_service"],
    )

    # Task A's own scoped figure must reflect only Task A's 2.0h, never the
    # resource-wide 7.0h across both tasks.
    assert snapshot_a.task_period_hours_label == "2.00h"
    # The resource-wide figure remains available, but as an explicitly
    # separate, clearly-labeled field (see time_builder.py), not as "Logged".
    assert snapshot_a.resource_period_total_hours_label == "7.00h"


def test_build_assignment_snapshot_planned_and_remaining_are_page_independent(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]

    project = ps.create_project("Planned Remaining Project")
    resource = rs.create_resource("Planned Remaining Resource", hourly_rate=60.0)
    project_resource = prs.add_to_project(
        project.id, resource.id, hourly_rate=60.0, currency_code="USD", planned_hours=20.0
    )
    task = ts.create_task(project.id, "Planned Remaining Task")
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    ts.update_assignment_planned_hours(
        assignment.id,
        allocated_planned_hours=Decimal("10"),
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    ts.add_time_entry(assignment.id, entry_date=date(2026, 5, 1), hours=4.0, note="Logged work")

    snapshot = build_assignment_snapshot(
        assignment.id,
        period_start=date(2026, 6, 1),  # a different, later period with no entries
        task_service=ts,
        timesheet_service=services["timesheet_service"],
    )

    # Planned/Logged(all-time)/Remaining must be correct regardless of which
    # period page is being viewed -- they are not derived from the ledger page.
    assert snapshot.planned_hours_label == "10.00h"
    assert snapshot.logged_hours_label == "4.00h"
    assert snapshot.remaining_hours_label == "6.00h"


# ---------------------------------------------------------------------------
# "Set Hours" UI affordance removed (Defect #4) -- ownership boundary
# ---------------------------------------------------------------------------


def test_task_assignment_hours_dialog_qml_file_was_removed():
    ui_qml_root = Path("src/ui_qml")
    path = (
        ui_qml_root
        / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentHoursDialog.qml"
    )
    assert not path.exists(), (
        "TaskAssignmentHoursDialog.qml should stay removed -- editing "
        "hours_logged from Assignment collides with Time's ownership of "
        "actual logged work now that Time Capture is the real path (see "
        "docs §43 defect D4)."
    )


def test_backend_set_assignment_hours_command_is_intentionally_retained(services):
    """The backend command is kept (not deleted) for non-UI/import paths,
    but is no longer reachable from any Task Detail QML dialog -- this test
    documents that decision so a future cleanup pass doesn't delete it by
    mistake believing it to be dead, nor re-add the UI affordance without
    revisiting the ownership boundary."""
    ts = services["task_service"]
    _, _, _, assignment = _setup_assignment(services)

    updated = ts.set_assignment_hours(assignment.id, Decimal("3.5"))
    assert updated.hours_logged == Decimal("3.5")


# ---------------------------------------------------------------------------
# Planned Work is settable at creation and editable afterwards (follow-up:
# Planned/Remaining must not be display-only with no way to ever set them)
# ---------------------------------------------------------------------------


def _setup_project_resource(services, *, planned_hours: float = 40.0):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    prs = services["project_resource_service"]
    project = ps.create_project("Planned Work Entry Project")
    resource = rs.create_resource("Planned Work Resource", hourly_rate=75.0)
    project_resource = prs.add_to_project(
        project.id, resource.id, hourly_rate=75.0, currency_code="USD", planned_hours=planned_hours
    )
    task = ts.create_task(project.id, "Planned Work Task")
    return ps, ts, rs, prs, project, resource, project_resource, task


def test_assign_project_resource_accepts_planned_hours_at_creation(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)

    assignment = ts.assign_project_resource(
        task_id=task.id,
        project_resource_id=project_resource.id,
        allocation_percent=100.0,
        allocated_planned_hours=Decimal("15"),
    )

    assert assignment.allocated_planned_hours == Decimal("15")


def test_assign_project_resource_rejects_planned_hours_beyond_envelope_at_creation(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(
        services, planned_hours=10.0
    )

    from src.core.platform.common.exceptions import BusinessRuleError

    with pytest.raises(BusinessRuleError) as exc:
        ts.assign_project_resource(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=100.0,
            allocated_planned_hours=Decimal("11"),
        )
    assert exc.value.code == "PROJECT_RESOURCE_HOURS_OVERALLOCATED"


def test_desktop_create_assignment_forwards_planned_hours_and_exposes_project_resource_version(
    services,
):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_service=ts, project_resource_service=prs, resource_service=rs,
    )

    from src.core.modules.project_management.api.desktop.tasks.commands.assignment_commands import (
        TaskAssignmentCreateCommand,
    )

    dto = api.create_assignment(
        TaskAssignmentCreateCommand(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=100.0,
            allocated_planned_hours=Decimal("8"),
        )
    )

    assert dto.allocated_planned_hours == "8"
    assert dto.project_resource_version == project_resource.version


def test_desktop_update_assignment_planned_hours_succeeds_with_correct_versions(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_service=ts, project_resource_service=prs, resource_service=rs,
    )
    assignment = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )

    from src.core.modules.project_management.api.desktop.tasks.commands.assignment_commands import (
        TaskAssignmentPlannedHoursCommand,
    )

    dto = api.update_assignment_planned_hours(
        TaskAssignmentPlannedHoursCommand(
            assignment_id=assignment.id,
            allocated_planned_hours=Decimal("20"),
            expected_assignment_version=assignment.version,
            expected_project_resource_version=project_resource.version,
        )
    )

    assert dto.allocated_planned_hours == "20"
    assert dto.version == assignment.version + 1


def test_desktop_update_assignment_planned_hours_stale_project_resource_version_fails_safe(
    services,
):
    """The dual optimistic-lock guards against two sibling assignments (on
    the same shared ProjectResource envelope) racing to redistribute planned
    hours -- NOT against the envelope itself being resized via
    ProjectResourceService.update(), which does not touch `version` at all
    (a separate, pre-existing gap noted in docs §43, out of this pass's
    scope since it lives in the ProjectResource/Planning aggregate)."""
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(
        services, planned_hours=40.0
    )
    task_b = ts.create_task(project.id, "Sibling Planned Work Task")
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_service=ts, project_resource_service=prs, resource_service=rs,
    )
    assignment_a = ts.assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=50.0
    )
    assignment_b = ts.assign_project_resource(
        task_id=task_b.id, project_resource_id=project_resource.id, allocation_percent=50.0
    )

    from src.core.modules.project_management.api.desktop.tasks.commands.assignment_commands import (
        TaskAssignmentPlannedHoursCommand,
    )

    # Assignment A allocates first -- this bumps project_resource.version.
    api.update_assignment_planned_hours(
        TaskAssignmentPlannedHoursCommand(
            assignment_id=assignment_a.id,
            allocated_planned_hours=Decimal("10"),
            expected_assignment_version=assignment_a.version,
            expected_project_resource_version=project_resource.version,
        )
    )

    # Assignment B still holds the pre-A-allocation project_resource version.
    with pytest.raises(ConcurrencyError) as exc:
        api.update_assignment_planned_hours(
            TaskAssignmentPlannedHoursCommand(
                assignment_id=assignment_b.id,
                allocated_planned_hours=Decimal("10"),
                expected_assignment_version=assignment_b.version,
                expected_project_resource_version=project_resource.version,  # now stale
            )
        )
    assert exc.value.code == "STALE_WRITE"


# ---------------------------------------------------------------------------
# list_assignments exposes per-row calendar capacity facts (Task Detail QML
# redesign follow-up, docs §44) -- the table's Capacity Status column and the
# inspector's Available/Committed/Headroom rows read these directly; QML
# performs no calculation of its own.
# ---------------------------------------------------------------------------


def test_list_assignments_exposes_within_capacity_for_a_lightly_loaded_resource(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("List Assignments Capacity Project")
    resource = rs.create_resource("List Assignments Capacity Resource", hourly_rate=50.0)
    window_start = date.today() + timedelta(days=1)
    task = ts.create_task(
        project.id, "List Assignments Capacity Task", start_date=window_start, duration_days=3
    )
    ts.assign_resource(task.id, resource.id, allocation_percent=20.0)

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_service=ts, resource_service=rs,
    )
    dtos = api.list_assignments(task.id)

    assert len(dtos) == 1
    assert dtos[0].capacity_known is True
    assert dtos[0].capacity_status == "AVAILABLE"
    assert dtos[0].capacity_status_label == "Within capacity"
    assert dtos[0].available_capacity_hours_label != ""
    assert dtos[0].committed_capacity_hours_label != ""
    assert dtos[0].remaining_planned_hours_label != ""


def test_list_assignments_exposes_over_capacity_for_a_double_booked_resource(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("List Assignments Over Capacity Project")
    resource = rs.create_resource("List Assignments Over Capacity Resource", hourly_rate=50.0)
    window_start = date.today() + timedelta(days=1)
    task_a = ts.create_task(
        project.id, "Over Capacity Task A", start_date=window_start, duration_days=3
    )
    task_b = ts.create_task(
        project.id, "Over Capacity Task B", start_date=window_start, duration_days=3
    )
    ts.assign_resource(task_a.id, resource.id, allocation_percent=70.0)
    ts.assign_resource(task_b.id, resource.id, allocation_percent=60.0)

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_service=ts, resource_service=rs,
    )
    dtos_a = api.list_assignments(task_a.id)
    dtos_b = api.list_assignments(task_b.id)

    # Each task's own row must reflect the resource's TOTAL same-project
    # commitment (70% + 60% = 130%), not just that one task's own share.
    assert len(dtos_a) == 1 and len(dtos_b) == 1
    assert dtos_a[0].capacity_status == "OVER_CAPACITY"
    assert dtos_b[0].capacity_status == "OVER_CAPACITY"
    assert dtos_a[0].capacity_status_label == "Over capacity"
    assert dtos_a[0].peak_utilization_percent > 100.0
    assert dtos_b[0].peak_utilization_percent > 100.0
