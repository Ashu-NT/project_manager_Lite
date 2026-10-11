from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def build_project_management_timesheets_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_lookup_query: TaskLookupQueryHandler | None = None,
    task_assignment_commands: TaskAssignmentCommandHandler | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
    resource_service: ResourceService | None = None,
    timesheet_service: TimesheetService | None = None,
) -> ProjectManagementTimesheetsDesktopApi:
    return ProjectManagementTimesheetsDesktopApi(
        project_service=project_service,
        task_lookup_query=task_lookup_query,
        task_assignment_commands=task_assignment_commands,
        module_catalog_service=module_catalog_service,
        resource_service=resource_service,
        timesheet_service=timesheet_service,
    )


__all__ = ["build_project_management_timesheets_desktop_api"]
