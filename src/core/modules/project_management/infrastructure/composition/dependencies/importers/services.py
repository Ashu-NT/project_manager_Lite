from __future__ import annotations

from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusHandler,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
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
    project_query: ProjectQueryHandler,
    project_create: ProjectCreateHandler,
    project_update: ProjectUpdateHandler,
    project_status: ProjectStatusHandler,
    task_capabilities: TaskImportCapabilities,
    resource_query: ResourceQueryHandler,
    resource_master_commands: ResourceMasterCommandHandler,
) -> DataImportService:
    return DataImportService(
        project_query=project_query,
        project_create=project_create,
        project_update=project_update,
        project_status=project_status,
        task_capabilities=task_capabilities,
        resource_query=resource_query,
        resource_master_commands=resource_master_commands,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
