from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.resources import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.timesheets import (
    TimesheetReviewQueryHandler,
    TimesheetWorkspaceCommandHandler,
    TimesheetWorkspaceQueryHandler,
)
from src.core.platform.application.time_management.time import (
    TimeEntryCommandHandler,
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
    TimesheetPeriodTransitionHandler,
)
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def build_project_management_timesheets_desktop_api(
    *,
    project_service: ProjectQueryHandler | None = None,
    task_lookup_query: TaskLookupQueryHandler | None = None,
    task_assignment_commands: TaskAssignmentCommandHandler | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
    resource_query: ResourceQueryHandler | None = None,
    timesheet_workspace_query: TimesheetWorkspaceQueryHandler | None = None,
    timesheet_workspace_commands: TimesheetWorkspaceCommandHandler | None = None,
    timesheet_review_query: TimesheetReviewQueryHandler | None = None,
    time_entry_commands: TimeEntryCommandHandler | None = None,
    time_entry_queries: TimeEntryQueryHandler | None = None,
    timesheet_period_query: TimesheetPeriodQueryHandler | None = None,
    timesheet_period_transitions: TimesheetPeriodTransitionHandler | None = None,
) -> ProjectManagementTimesheetsDesktopApi:
    return ProjectManagementTimesheetsDesktopApi(
        project_service=project_service,
        task_lookup_query=task_lookup_query,
        task_assignment_commands=task_assignment_commands,
        module_catalog_service=module_catalog_service,
        resource_query=resource_query,
        timesheet_workspace_query=timesheet_workspace_query,
        timesheet_workspace_commands=timesheet_workspace_commands,
        timesheet_review_query=timesheet_review_query,
        time_entry_commands=time_entry_commands,
        time_entry_queries=time_entry_queries,
        timesheet_period_query=timesheet_period_query,
        timesheet_period_transitions=timesheet_period_transitions,
    )


__all__ = ["build_project_management_timesheets_desktop_api"]
