from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.api import (
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService


def build_project_management_timesheets_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    resource_service: ResourceService | None = None,
    timesheet_service: TimesheetService | None = None,
) -> ProjectManagementTimesheetsDesktopApi:
    return ProjectManagementTimesheetsDesktopApi(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        timesheet_service=timesheet_service,
    )


__all__ = ["build_project_management_timesheets_desktop_api"]
