"""Task Detail (Assignment + Time) backend coverage: optimistic-concurrency on
allocation edits, read-side exposure of allocated_planned_hours/version, the
task-scoped (not resource-wide) Time Summary fix, and removal of the "Set Hours"
UI affordance."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_resources import (
    ProjectResourceAssignCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskAssignmentPlannedHoursCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.ui_qml.modules.project_management.presenters.tasks.assignment_mapper import (
    to_assignment_record_view_model,
)


def _setup_assignment(services, *, allocation_percent: float = 50.0):
    project = services['project_create'].create_project(ProjectCreateCommand(name="Assignment Concurrency Project"))
    task = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Concurrency Task"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Concurrency Resource", hourly_rate=90.0))
    assignment = services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=allocation_percent)
    return project, task, resource, assignment


# ---------------------------------------------------------------------------
# set_assignment_allocation — optimistic concurrency (Defect #2)
# ---------------------------------------------------------------------------


def test_set_assignment_allocation_with_expected_version_succeeds_and_increments_version(services):
    _, _, _, assignment = _setup_assignment(services)

    updated = services['task_assignment_commands'].set_assignment_allocation(TaskAssignmentAllocationCommand(assignment_id=assignment.id, allocation_percent=75.0, expected_version=assignment.version))

    assert updated.allocation_percent == 75.0
    assert updated.version == assignment.version + 1


def test_set_assignment_allocation_stale_version_raises_concurrency_error(services):
    _, _, _, assignment = _setup_assignment(services)

    services['task_assignment_commands'].set_assignment_allocation(TaskAssignmentAllocationCommand(assignment_id=assignment.id, allocation_percent=60.0, expected_version=assignment.version))

    with pytest.raises(ConcurrencyError) as exc:
        services['task_assignment_commands'].set_assignment_allocation(TaskAssignmentAllocationCommand(assignment_id=assignment.id, allocation_percent=80.0, expected_version=assignment.version))
    assert exc.value.code == "STALE_WRITE"


def test_set_assignment_allocation_requires_expected_version(services):
    """`expected_version` is a required keyword-only argument, not an optional bypass -- every
    caller must supply the version it read."""
    _, _, _, assignment = _setup_assignment(services)

    with pytest.raises(TypeError):
        services['task_assignment_commands'].set_assignment_allocation(TaskAssignmentAllocationCommand(assignment_id=assignment.id, allocation_percent=65.0))

    updated = services['task_assignment_commands'].set_assignment_allocation(TaskAssignmentAllocationCommand(assignment_id=assignment.id, allocation_percent=65.0, expected_version=assignment.version))
    assert updated.allocation_percent == 65.0


# ---------------------------------------------------------------------------
# Desktop API read-side exposure of allocated_planned_hours / version (Defect #1)
# ---------------------------------------------------------------------------


def test_task_assignment_desktop_dto_exposes_planned_hours_and_version(services):
    ps = services['project_query']
    rs = services["resource_query"]
    prs = services["project_resource_query"]

    project = services['project_create'].create_project(ProjectCreateCommand(name="Planned Hours Exposure Project"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Planned Hours Resource", hourly_rate=80.0))
    project_resource = services["project_resource_commands"].add_to_project(ProjectResourceAssignCommand(project_id=project.id, resource_id=resource.id, hourly_rate=80.0, currency_code="USD", planned_hours=40.0))
    task = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Planned Hours Task"))
    assignment = services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0))
    services['task_assignment_commands'].update_assignment_planned_hours(TaskAssignmentPlannedHoursCommand(assignment_id=assignment.id, allocated_planned_hours=Decimal(12), expected_assignment_version=assignment.version, expected_project_resource_version=project_resource.version))

    api = build_project_management_tasks_desktop_api(
        project_service=ps,
        task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'],
        project_resource_query=prs,
        resource_query=rs,
    )
    dtos = api.list_assignments(task.id)
    assert len(dtos) == 1
    assert dtos[0].allocated_planned_hours == Decimal("12")
    assert dtos[0].version == 2


# ---------------------------------------------------------------------------
# Time Summary is task-scoped, not resource-wide (Defect #3)
# ---------------------------------------------------------------------------


def test_canonical_time_summary_logged_is_task_scoped_not_resource_wide(services):

    project = services['project_create'].create_project(ProjectCreateCommand(name="Scope Leak Project"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Shared Resource", hourly_rate=70.0))

    task_a = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Task A"))
    task_b = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Task B"))
    assignment_a = services['task_assignment_commands'].assign_resource(task_a.id, resource.id, allocation_percent=50.0)
    assignment_b = services['task_assignment_commands'].assign_resource(task_b.id, resource.id, allocation_percent=50.0)

    entry_date = date(2026, 4, 6)
    services["time_entry_commands"].add_time_entry(assignment_a.id, entry_date=entry_date, hours=2.0, note="Task A work")
    services["time_entry_commands"].add_time_entry(assignment_b.id, entry_date=entry_date, hours=5.0, note="Task B work")

    summary = services['task_assignment_commands'].get_task_time_summary(task_a.id)
    assert summary.actual_hours == Decimal("2")
    resource_period = services["timesheet_period_query"].summarize_timesheet_period(
        resource.id, period_start=date(2026, 4, 1),
    )
    assert resource_period.total_hours == 7.0


def test_canonical_time_summary_planned_and_remaining_are_period_independent(services):
    services["project_resource_query"]

    project = services['project_create'].create_project(ProjectCreateCommand(name="Planned Remaining Project"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Planned Remaining Resource", hourly_rate=60.0))
    project_resource = services["project_resource_commands"].add_to_project(ProjectResourceAssignCommand(project_id=project.id, resource_id=resource.id, hourly_rate=60.0, currency_code="USD", planned_hours=20.0))
    task = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Planned Remaining Task"))
    assignment = services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0))
    services['task_assignment_commands'].update_assignment_planned_hours(TaskAssignmentPlannedHoursCommand(assignment_id=assignment.id, allocated_planned_hours=Decimal(10), expected_assignment_version=assignment.version, expected_project_resource_version=project_resource.version))
    services["time_entry_commands"].add_time_entry(assignment.id, entry_date=date(2026, 5, 1), hours=4.0, note="Logged work")

    assert services["time_entry_queries"].list_time_entries_for_assignment_period(
        assignment.id, period_start=date(2026, 6, 1),
    ) == []
    summary = services['task_assignment_commands'].get_task_time_summary(task.id)
    assert summary.planned_hours == Decimal("10")
    assert summary.actual_hours == Decimal("4")
    assert summary.remaining_hours == Decimal("6")


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
        "actual logged work now that Time Capture is the real path."
    )


def test_backend_set_assignment_hours_command_is_intentionally_retained(services):
    """The assignment command remains available without a Task Detail dialog."""
    _, _, _, assignment = _setup_assignment(services)

    updated = services["task_assignment_commands"].set_assignment_hours(
        TaskAssignmentHoursCommand(assignment.id, Decimal("3.5"))
    )
    assert updated.hours_logged == Decimal("3.5")


# ---------------------------------------------------------------------------
# Planned Work is settable at creation and editable afterwards (follow-up:
# Planned/Remaining must not be display-only with no way to ever set them)
# ---------------------------------------------------------------------------


def _setup_project_resource(services, *, planned_hours: float = 40.0):
    ps = services['project_query']
    ts = services['task_lookup_query']
    rs = services["resource_query"]
    prs = services["project_resource_query"]
    project = services['project_create'].create_project(ProjectCreateCommand(name="Planned Work Entry Project"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="Planned Work Resource", hourly_rate=75.0))
    project_resource = services["project_resource_commands"].add_to_project(ProjectResourceAssignCommand(project_id=project.id, resource_id=resource.id, hourly_rate=75.0, currency_code="USD", planned_hours=planned_hours))
    task = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Planned Work Task"))
    return ps, ts, rs, prs, project, resource, project_resource, task


def test_assign_project_resource_accepts_planned_hours_at_creation(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)

    assignment = services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0, allocated_planned_hours=Decimal(15)))

    assert assignment.allocated_planned_hours == Decimal(15)


def test_assign_project_resource_rejects_planned_hours_beyond_envelope_at_creation(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(
        services, planned_hours=10.0
    )

    from src.core.platform.common.exceptions import BusinessRuleError

    with pytest.raises(BusinessRuleError) as exc:
        services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0, allocated_planned_hours=Decimal(11)))
    assert exc.value.code == "PROJECT_RESOURCE_HOURS_OVERALLOCATED"


def test_desktop_create_assignment_forwards_planned_hours_and_exposes_project_resource_version(
    services,
):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'], project_resource_query=prs, resource_query=rs,
    )

    from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
        TaskAssignmentCreateCommand,
    )

    dto = api.create_assignment(
        TaskAssignmentCreateCommand(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=100.0,
            allocated_planned_hours=Decimal(8),
        )
    )

    assert dto.allocated_planned_hours == Decimal("8")
    assert dto.project_resource_version == project_resource.version


def test_desktop_update_assignment_planned_hours_succeeds_with_correct_versions(services):
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(services)
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'], project_resource_query=prs, resource_query=rs,
    )
    assignment = services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0))

    from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
        TaskAssignmentPlannedHoursCommand,
    )

    dto = api.update_assignment_planned_hours(
        TaskAssignmentPlannedHoursCommand(
            assignment_id=assignment.id,
            allocated_planned_hours=Decimal(20),
            expected_assignment_version=assignment.version,
            expected_project_resource_version=project_resource.version,
        )
    )

    assert dto.allocated_planned_hours == Decimal("20")
    assert dto.version == assignment.version + 1


def test_desktop_update_assignment_planned_hours_stale_project_resource_version_fails_safe(
    services,
):
    """The dual optimistic-lock guards against two sibling assignments (on
    the same shared ProjectResource envelope) racing to redistribute planned
    hours -- NOT against the envelope itself being resized via
    ProjectResourceQueryHandler.update(), which does not touch `version` at all."""
    ps, ts, rs, prs, project, resource, project_resource, task = _setup_project_resource(
        services, planned_hours=40.0
    )
    task_b = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Sibling Planned Work Task"))
    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'], project_resource_query=prs, resource_query=rs,
    )
    assignment_a = services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task.id, project_resource_id=project_resource.id, allocation_percent=50.0))
    assignment_b = services['task_assignment_commands'].assign_project_resource(TaskAssignmentCreateCommand(task_id=task_b.id, project_resource_id=project_resource.id, allocation_percent=50.0))

    from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
        TaskAssignmentPlannedHoursCommand,
    )

    # Assignment A allocates first -- this bumps project_resource.version.
    api.update_assignment_planned_hours(
        TaskAssignmentPlannedHoursCommand(
            assignment_id=assignment_a.id,
            allocated_planned_hours=Decimal(10),
            expected_assignment_version=assignment_a.version,
            expected_project_resource_version=project_resource.version,
        )
    )

    # Assignment B still holds the pre-A-allocation project_resource version.
    with pytest.raises(ConcurrencyError) as exc:
        api.update_assignment_planned_hours(
            TaskAssignmentPlannedHoursCommand(
                assignment_id=assignment_b.id,
                allocated_planned_hours=Decimal(10),
                expected_assignment_version=assignment_b.version,
                expected_project_resource_version=project_resource.version,  # now stale
            )
        )
    assert exc.value.code == "STALE_WRITE"


# ---------------------------------------------------------------------------
# list_assignments exposes per-row calendar capacity facts -- the table's
# Capacity Status column and the inspector's Available/Committed/Headroom
# rows read these directly; QML performs no calculation of its own.
# ---------------------------------------------------------------------------


def test_list_assignments_exposes_within_capacity_for_a_lightly_loaded_resource(services):
    ps = services['project_query']
    rs = services["resource_query"]

    project = services['project_create'].create_project(ProjectCreateCommand(name="List Assignments Capacity Project"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="List Assignments Capacity Resource", hourly_rate=50.0))
    window_start = date.today() + timedelta(days=1)
    task = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="List Assignments Capacity Task", start_date=window_start, duration_days=3))
    services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=20.0)

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'], resource_query=rs,
    )
    dtos = api.list_assignments(task.id)

    assert len(dtos) == 1
    assert dtos[0].capacity is not None
    view = to_assignment_record_view_model(dtos[0])
    assert view.state["capacityKnown"] is True
    assert dtos[0].capacity.capacity_status == "AVAILABLE"
    assert view.state["capacityStatusLabel"] == "Within capacity"
    assert view.state["availableCapacityLabel"] != ""
    assert view.state["committedCapacityLabel"] != ""
    assert view.state["remainingPlannedLabel"] != ""


def test_list_assignments_exposes_over_capacity_for_a_double_booked_resource(services):
    ps = services['project_query']
    rs = services["resource_query"]

    project = services['project_create'].create_project(ProjectCreateCommand(name="List Assignments Over Capacity Project"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="List Assignments Over Capacity Resource", hourly_rate=50.0))
    window_start = date.today() + timedelta(days=1)
    task_a = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Over Capacity Task A", start_date=window_start, duration_days=3))
    task_b = services['task_lifecycle_commands'].create_task(TaskCreateCommand(project_id=project.id, name="Over Capacity Task B", start_date=window_start, duration_days=3))
    services['task_assignment_commands'].assign_resource(task_a.id, resource.id, allocation_percent=70.0)
    services['task_assignment_commands'].assign_resource(task_b.id, resource.id, allocation_percent=60.0)

    api = build_project_management_tasks_desktop_api(
        project_service=ps, task_lookup_query=services['task_lookup_query'], task_hierarchy_query=services['task_hierarchy_query'], task_deletion_commands=services['task_deletion_commands'], task_progress_commands=services['task_progress_commands'], task_hierarchy_commands=services['task_hierarchy_commands'], task_constraint_commands=services['task_constraint_commands'], task_lifecycle_commands=services['task_lifecycle_commands'], task_dependency_commands=services['task_dependency_commands'], task_dependency_query=services['task_dependency_query'], task_detail_query=services['task_detail_query'], task_assignment_commands=services['task_assignment_commands'], resource_query=rs,
    )
    dtos_a = api.list_assignments(task_a.id)
    dtos_b = api.list_assignments(task_b.id)

    # Each task's own row must reflect the resource's TOTAL same-project
    # commitment (70% + 60% = 130%), not just that one task's own share.
    assert len(dtos_a) == 1 and len(dtos_b) == 1
    assert dtos_a[0].capacity is not None
    assert dtos_b[0].capacity is not None
    assert dtos_a[0].capacity.capacity_status == "OVER_CAPACITY"
    assert dtos_b[0].capacity.capacity_status == "OVER_CAPACITY"
    assert to_assignment_record_view_model(dtos_a[0]).state["capacityStatusLabel"] == "Over capacity"
    assert dtos_a[0].capacity.peak_utilization_percent > 100.0
    assert dtos_b[0].capacity.peak_utilization_percent > 100.0
