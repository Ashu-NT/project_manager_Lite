from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.resources import (
    ResourceAvailabilityService,
    ResourceService,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
)
from src.core.platform.employee import EmployeeService


def build_project_management_resources_desktop_api(
    *,
    resource_service: ResourceService | None = None,
    employee_service: EmployeeService | None = None,
    availability_service: ResourceAvailabilityService | None = None,
    task_service: object | None = None,
    assignment_repo: AssignmentRepository | None = None,
    project_service: object | None = None,
    work_calendar_engine: CalendarProtocol | None = None,
) -> ProjectManagementResourcesDesktopApi:
    return ProjectManagementResourcesDesktopApi(
        resource_service=resource_service,
        employee_service=employee_service,
        availability_service=availability_service,
        task_service=task_service,
        assignment_repo=assignment_repo,
        project_service=project_service,
        work_calendar_engine=work_calendar_engine,
    )


__all__ = ["build_project_management_resources_desktop_api"]
