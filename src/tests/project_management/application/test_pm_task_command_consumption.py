from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.api.desktop.tasks.api import (
    ProjectManagementTasksDesktopApi,
)
from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.application.collaboration.dto.commands.comment_reactions import (
    TaskCollaborationReactionCommand,
)
from src.core.modules.project_management.application.collaboration.dto.commands.task_comments import (
    TaskCollaborationDeleteCommand,
    TaskCollaborationEditCommand,
    TaskCollaborationPostCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
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
from src.core.modules.project_management.application.tasks.dto.commands.task_constraints import (
    TaskConstraintUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_hierarchy import (
    TaskWbsMoveCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
    TaskUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskBulkStatusCommand,
    TaskProgressCommand,
)
from src.core.modules.project_management.application.timesheets.dto.commands.time_entries import (
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)


class HandlerReached(Exception):
    pass


@pytest.mark.parametrize(
    "api_type,capability,desktop_method,handler_method,command",
    [
        (
            ProjectManagementTasksDesktopApi,
            "task_lifecycle_commands",
            "create_task",
            "create_task",
            TaskCreateCommand("p", "Task"),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_lifecycle_commands",
            "update_task",
            "update_task",
            TaskUpdateCommand("t", "Task"),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_progress_commands",
            "update_progress",
            "update_progress",
            TaskProgressCommand("t", percent_complete=0),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_progress_commands",
            "apply_bulk_status",
            "set_tasks_status",
            TaskBulkStatusCommand(("t",), "TODO"),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_hierarchy_commands",
            "move_task",
            "move_task",
            TaskWbsMoveCommand("t", None),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_constraint_commands",
            "update_task_scheduling_constraint",
            "update_task_scheduling_constraint",
            TaskConstraintUpdateCommand("t"),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_assignment_commands",
            "create_assignment",
            "assign_project_resource",
            TaskAssignmentCreateCommand("t", "pr"),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_assignment_commands",
            "update_assignment_allocation",
            "set_assignment_allocation",
            TaskAssignmentAllocationCommand("a", 0, 1),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_assignment_commands",
            "set_assignment_hours",
            "set_assignment_hours",
            TaskAssignmentHoursCommand("a", Decimal(0)),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_assignment_commands",
            "update_assignment_planned_hours",
            "update_assignment_planned_hours",
            TaskAssignmentPlannedHoursCommand("a", Decimal(0), 1, 1),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_dependency_commands",
            "create_dependency",
            "add_dependency",
            TaskDependencyCreateCommand("t", "other", "PREDECESSOR"),
        ),
        (
            ProjectManagementTasksDesktopApi,
            "task_dependency_commands",
            "update_dependency",
            "update_dependency",
            TaskDependencyUpdateCommand("d"),
        ),
        (
            ProjectManagementCollaborationDesktopApi,
            "comment_commands",
            "post_task_comment",
            "post_comment",
            TaskCollaborationPostCommand("t", "Hello"),
        ),
        (
            ProjectManagementCollaborationDesktopApi,
            "comment_commands",
            "edit_task_comment",
            "edit_comment",
            TaskCollaborationEditCommand("c", "Edited", 1),
        ),
        (
            ProjectManagementCollaborationDesktopApi,
            "comment_commands",
            "delete_task_comment",
            "delete_comment",
            TaskCollaborationDeleteCommand("c", 1),
        ),
        (
            ProjectManagementCollaborationDesktopApi,
            "comment_engagement",
            "react_to_task_comment",
            "react_to_comment",
            TaskCollaborationReactionCommand("c", "+1"),
        ),
        (
            ProjectManagementCollaborationDesktopApi,
            "comment_engagement",
            "remove_task_comment_reaction",
            "remove_reaction",
            TaskCollaborationReactionCommand("c", "+1"),
        ),
        (
            ProjectManagementTimesheetsDesktopApi,
            "timesheet_workspace_commands",
            "add_time_entry",
            "add_timesheet_entry",
            TimesheetEntryCreateCommand("a", date(2026, 3, 2), 1),
        ),
        (
            ProjectManagementTimesheetsDesktopApi,
            "timesheet_workspace_commands",
            "update_time_entry",
            "update_timesheet_entry",
            TimesheetEntryUpdateCommand("e", 1, hours=0),
        ),
    ],
)
def test_desktop_passes_original_command(
    api_type, capability, desktop_method, handler_method, command
):
    handler = Mock(side_effect=HandlerReached)
    api = api_type(**{capability: SimpleNamespace(**{handler_method: handler})})
    with pytest.raises(HandlerReached):
        getattr(api, desktop_method)(command)
    handler.assert_called_once_with(command)


def _task(services, **kwargs):
    project = ProjectManagementProjectsDesktopApi(
        project_create=services["project_create"]
    ).create_project(ProjectCreateCommand(name="Command project"))
    return services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(project.id, "Command task", **kwargs)
    )


def test_lifecycle_consumes_status_and_preserves_progress_transitions(services):
    task = _task(services, status="DONE")
    assert task.status == TaskStatus.DONE
    assert task.percent_complete == 100
    lifecycle = services["task_lifecycle_commands"]
    updated = lifecycle.update_task(
        TaskUpdateCommand(
            task.id, "Reopened", status="IN_PROGRESS", expected_version=task.version
        )
    )
    assert updated.status == TaskStatus.IN_PROGRESS
    assert updated.percent_complete == 50
    with pytest.raises(ConcurrencyError):
        lifecycle.update_task(TaskUpdateCommand(task.id, "Stale", expected_version=0))
    progressed = services["task_progress_commands"].update_progress(
        TaskProgressCommand(
            task.id, percent_complete=0, expected_version=updated.version
        )
    )
    assert progressed.percent_complete == 0
    assert progressed.status == TaskStatus.TODO


def test_collaboration_commands_preserve_revision_and_reactions(services):
    task = _task(services)
    commands = services["collaboration_comment_commands"]
    engagement = services["collaboration_comment_engagement"]
    comment = commands.post_comment(TaskCollaborationPostCommand(task.id, "Original"))
    edited = commands.edit_comment(
        TaskCollaborationEditCommand(comment.id, "Edited", comment.version)
    )
    with pytest.raises(ConcurrencyError):
        commands.edit_comment(TaskCollaborationEditCommand(comment.id, "Stale", 0))
    reacted = engagement.react_to_comment(
        TaskCollaborationReactionCommand(comment.id, "+1")
    )
    assert reacted.reactions["+1"]
    removed = engagement.remove_reaction(
        TaskCollaborationReactionCommand(comment.id, "+1")
    )
    assert not removed.reactions.get("+1")
    deleted = commands.delete_comment(
        TaskCollaborationDeleteCommand(comment.id, removed.version)
    )
    assert deleted.deleted_at is not None
    assert edited.body == "Edited"


def test_timesheet_commands_keep_time_owned_versions_and_decimal_hours(services):
    task = _task(services)
    resource = ProjectManagementResourcesDesktopApi(
        resource_master_commands=services["resource_master_commands"]
    ).create_resource(ResourceCreateCommand(name="Command worker"))
    assignment = services["task_assignment_commands"].assign_resource(
        task.id, resource.id
    )
    assignment = services["task_assignment_commands"].set_assignment_hours(
        TaskAssignmentHoursCommand(assignment.id, Decimal("0.00"))
    )
    assert assignment.hours_logged == Decimal(0)
    commands = services["timesheet_workspace_commands"]
    entry = commands.add_timesheet_entry(
        TimesheetEntryCreateCommand(assignment.id, date(2026, 3, 2), 2, "Work")
    )
    updated = commands.update_timesheet_entry(
        TimesheetEntryUpdateCommand(entry.id, entry.version, hours=3, note="")
    )
    assert updated.hours == 3
    assert updated.note == ""
    with pytest.raises(ConcurrencyError):
        commands.update_timesheet_entry(
            TimesheetEntryUpdateCommand(entry.id, 0, hours=4)
        )


def test_dependency_and_constraint_commands_keep_schedule_validation(services):
    first = _task(services, start_date=date(2026, 3, 2), duration_days=2)
    second = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(
            first.project_id, "Successor", start_date=date(2026, 3, 4), duration_days=1
        )
    )
    dependencies = services["task_dependency_commands"]
    dependency = dependencies.add_dependency(
        TaskDependencyCreateCommand(second.id, first.id, " predecessor ", lag_days=0)
    )
    assert dependency.predecessor_task_id == first.id
    assert dependency.successor_task_id == second.id
    updated = dependencies.update_dependency(
        TaskDependencyUpdateCommand(
            dependency.id, lag_days=1, expected_version=dependency.version
        )
    )
    assert updated.lag_days == 1
    with pytest.raises(ConcurrencyError):
        dependencies.update_dependency(
            TaskDependencyUpdateCommand(dependency.id, expected_version=0)
        )
    constraint = services["task_constraint_commands"]
    current = services["task_detail_query"].get_task(first.id)
    cleared = constraint.update_task_scheduling_constraint(
        TaskConstraintUpdateCommand(first.id, expected_version=current.version)
    )
    assert cleared.constraint_type is None


def test_hierarchy_commands_keep_expected_version(services):
    parent = _task(services)
    child = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(parent.project_id, "Child")
    )
    hierarchy = services["task_hierarchy_commands"]
    moved = hierarchy.move_task(
        TaskWbsMoveCommand(child.id, parent.id, expected_version=child.version)
    )
    assert moved.parent_task_id == parent.id
    with pytest.raises(ConcurrencyError):
        hierarchy.move_task(TaskWbsMoveCommand(child.id, None, expected_version=0))


def test_scoped_timesheet_command_still_checks_resource_and_period(services):
    task = _task(services)
    resource = ProjectManagementResourcesDesktopApi(
        resource_master_commands=services["resource_master_commands"]
    ).create_resource(ResourceCreateCommand(name="Scoped worker"))
    assignment = services["task_assignment_commands"].assign_resource(
        task.id, resource.id
    )
    commands = services["timesheet_workspace_commands"]
    entry = commands.add_timesheet_entry(
        TimesheetEntryCreateCommand(assignment.id, date(2026, 3, 2), 1),
        scope="all",
        resource_id=resource.id,
        period_start=date(2026, 3, 2),
    )
    with pytest.raises(ValidationError, match="reporting period"):
        commands.update_timesheet_entry(
            TimesheetEntryUpdateCommand(
                entry.id, entry.version, entry_date=date(2026, 4, 1)
            ),
            scope="all",
            resource_id=resource.id,
            period_start=date(2026, 3, 2),
        )


def test_commands_still_fail_closed_when_module_is_disabled(services, monkeypatch):
    handler = services["task_lifecycle_commands"]
    monkeypatch.setattr(
        handler,
        "_module_catalog_service",
        SimpleNamespace(
            get_entitlement=lambda _code: SimpleNamespace(
                runtime_enabled=False,
                label="Project Management",
                lifecycle_status="inactive",
            )
        ),
    )
    with pytest.raises(BusinessRuleError, match="not enabled"):
        handler.create_task(TaskCreateCommand("p", "Blocked"))


def test_comment_command_audit_failure_rolls_back(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    task = _task(services)

    def fail_audit(self, **kwargs):
        raise RuntimeError("command audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", fail_audit)
    with pytest.raises(RuntimeError, match="command audit failure"):
        services["collaboration_comment_commands"].post_comment(
            TaskCollaborationPostCommand(task.id, "Must roll back")
        )
    assert services["collaboration_comment_query"].query_task_comments_page(task.id).items == ()


def test_assignment_commands_keep_decimal_zero_and_versions(services):
    task = _task(services)
    resource = ProjectManagementResourcesDesktopApi(
        resource_master_commands=services["resource_master_commands"]
    ).create_resource(ResourceCreateCommand(name="Assignment worker"))
    commands = services["task_assignment_commands"]
    first = commands.assign_resource(task.id, resource.id)
    other = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(task.project_id, "Other task")
    )
    assigned = commands.assign_project_resource(
        TaskAssignmentCreateCommand(
            other.id, first.project_resource_id, allocated_planned_hours=Decimal("0.00")
        )
    )
    allocated = commands.set_assignment_allocation(
        TaskAssignmentAllocationCommand(assigned.id, 25, assigned.version)
    )
    assert allocated.allocation_percent == 25
    project_resource = services["project_resource_query"].get(first.project_resource_id)
    planned = commands.update_assignment_planned_hours(
        TaskAssignmentPlannedHoursCommand(
            allocated.id, Decimal("0.00"), allocated.version, project_resource.version
        )
    )
    assert planned.allocated_planned_hours == Decimal(0)
    with pytest.raises(ConcurrencyError):
        commands.set_assignment_allocation(TaskAssignmentAllocationCommand(planned.id, 50, 0))
