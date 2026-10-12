from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.resources import (
    ResourceService,
    ResourceWorkloadService,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def build_project_management_resources_desktop_api(
    *,
    resource_service: ResourceService | None = None,
    resource_capability_query: ResourceCapabilityQueryHandler | None = None,
    resource_context_query: ResourceContextQueryHandler | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
    employee_service: EmployeeService | None = None,
    workload_service: ResourceWorkloadService | None = None,
    department_service: object | None = None,
    site_service: object | None = None,
) -> ProjectManagementResourcesDesktopApi:
    return ProjectManagementResourcesDesktopApi(
        resource_service=resource_service,
        resource_capability_query=resource_capability_query,
        resource_context_query=resource_context_query,
        module_catalog_service=module_catalog_service,
        employee_service=employee_service,
        workload_service=workload_service,
        department_service=department_service,
        site_service=site_service,
    )


__all__ = ["build_project_management_resources_desktop_api"]
