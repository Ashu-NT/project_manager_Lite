from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.resources import (
    ResourceCapabilityCommandHandler,
    ResourceMasterCommandHandler,
    ResourceQueryHandler,
    ResourceWorkloadQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)
from src.core.platform.application.master_data.employee import EmployeeQueryHandler
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def build_project_management_resources_desktop_api(
    *,
    resource_query: ResourceQueryHandler | None = None,
    resource_master_commands: ResourceMasterCommandHandler | None = None,
    resource_capability_commands: ResourceCapabilityCommandHandler | None = None,
    resource_capability_query: ResourceCapabilityQueryHandler | None = None,
    resource_context_query: ResourceContextQueryHandler | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
    employee_query: EmployeeQueryHandler | None = None,
    workload_service: ResourceWorkloadQueryHandler | None = None,
    department_query: object | None = None,
    site_query: object | None = None,
) -> ProjectManagementResourcesDesktopApi:
    return ProjectManagementResourcesDesktopApi(
        resource_query=resource_query,
        resource_master_commands=resource_master_commands,
        resource_capability_commands=resource_capability_commands,
        resource_capability_query=resource_capability_query,
        resource_context_query=resource_context_query,
        module_catalog_service=module_catalog_service,
        employee_query=employee_query,
        workload_service=workload_service,
        department_query=department_query,
        site_query=site_query,
    )


__all__ = ["build_project_management_resources_desktop_api"]
