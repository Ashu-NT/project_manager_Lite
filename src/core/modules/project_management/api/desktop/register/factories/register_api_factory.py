from __future__ import annotations

from src.core.modules.project_management.api.desktop.register.api import (
    ProjectManagementRegisterDesktopApi,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.risk import RegisterQueryHandler
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)


def build_project_management_register_desktop_api(
    *,
    project_service: ProjectService | None = None,
    register_query: RegisterQueryHandler | None = None,
    register_lifecycle_commands: RegisterLifecycleHandler | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
) -> ProjectManagementRegisterDesktopApi:
    return ProjectManagementRegisterDesktopApi(
        project_service=project_service,
        register_query=register_query,
        register_lifecycle_commands=register_lifecycle_commands,
        module_catalog_service=module_catalog_service,
    )


__all__ = ["build_project_management_register_desktop_api"]
