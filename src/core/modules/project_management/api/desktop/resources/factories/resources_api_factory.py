from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.resources import (
    ResourceService,
    ResourceWorkloadService,
)
from src.core.platform.application.master_data.employee.employee_service import EmployeeService


def build_project_management_resources_desktop_api(
    *,
    resource_service: ResourceService | None = None,
    employee_service: EmployeeService | None = None,
    workload_service: ResourceWorkloadService | None = None,
    task_service: object | None = None,
    project_service: object | None = None,
    department_service: object | None = None,
    site_service: object | None = None,
) -> ProjectManagementResourcesDesktopApi:
    return ProjectManagementResourcesDesktopApi(
        resource_service=resource_service,
        employee_service=employee_service,
        workload_service=workload_service,
        task_service=task_service,
        project_service=project_service,
        department_service=department_service,
        site_service=site_service,
    )


__all__ = ["build_project_management_resources_desktop_api"]
