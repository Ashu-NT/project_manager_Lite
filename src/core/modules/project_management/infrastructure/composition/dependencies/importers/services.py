from __future__ import annotations

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_data_import_service(
    platform_services: PlatformServiceBundle,
    *,
    project_service: ProjectService,
    task_service: TaskService,
    resource_service: ResourceService,
) -> DataImportService:
    return DataImportService(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
