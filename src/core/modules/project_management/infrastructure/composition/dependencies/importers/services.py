from __future__ import annotations

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ResourceMasterCommandHandler,
    ResourceQueryHandler,
)
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.modules.project_management.infrastructure.importers.tasks.capabilities import (
    TaskImportCapabilities,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_data_import_service(
    platform_services: PlatformServiceBundle,
    *,
    project_service: ProjectService,
    task_capabilities: TaskImportCapabilities,
    resource_query: ResourceQueryHandler,
    resource_master_commands: ResourceMasterCommandHandler,
) -> DataImportService:
    return DataImportService(
        project_service=project_service,
        task_capabilities=task_capabilities,
        resource_query=resource_query,
        resource_master_commands=resource_master_commands,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
