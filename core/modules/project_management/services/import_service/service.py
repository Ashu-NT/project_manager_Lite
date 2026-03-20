from __future__ import annotations

from pathlib import Path

from core.platform.importing import CsvImportRuntime, ImportDefinitionRegistry
from core.modules.project_management.importing import register_project_management_import_definitions
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.project import ProjectService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.task import TaskService

from .execution import DataImportExecutionMixin
from .models import ImportFieldSpec, ImportPreview, ImportSummary
from .preview import DataImportPreviewMixin
from .schemas import IMPORT_SCHEMAS
from .support import DataImportSupportMixin


class DataImportService(
    ProjectManagementModuleGuardMixin,
    DataImportExecutionMixin,
    DataImportPreviewMixin,
    DataImportSupportMixin,
):
    _SCHEMAS: dict[str, tuple[ImportFieldSpec, ...]] = IMPORT_SCHEMAS

    def __init__(
        self,
        *,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        cost_service: CostService,
        module_catalog_service=None,
        import_registry: ImportDefinitionRegistry | None = None,
        import_runtime: CsvImportRuntime | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._cost_service = cost_service
        self._module_catalog_service = module_catalog_service
        registry = import_registry or ImportDefinitionRegistry()
        register_project_management_import_definitions(
            registry,
            schemas=self._SCHEMAS,
            preview_handlers={
                "projects": self._preview_projects,
                "resources": self._preview_resources,
                "tasks": self._preview_tasks,
                "costs": self._preview_costs,
            },
            execution_handlers={
                "projects": self._import_projects,
                "resources": self._import_resources,
                "tasks": self._import_tasks,
                "costs": self._import_costs,
            },
        )
        self._import_registry = registry
        self._import_runtime = import_runtime or CsvImportRuntime(registry)

    def get_import_schema(self, entity_type: str) -> tuple[ImportFieldSpec, ...]:
        return self._import_runtime.get_import_schema(entity_type)

    def read_csv_columns(self, file_path: str | Path) -> list[str]:
        return self._import_runtime.read_csv_columns(file_path)

    def preview_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        max_rows: int = 100,
    ) -> ImportPreview:
        return self._import_runtime.preview_csv(
            entity_type,
            file_path,
            column_mapping=column_mapping,
            max_rows=max_rows,
        )

    def import_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
    ) -> ImportSummary:
        return self._import_runtime.import_csv(
            entity_type,
            file_path,
            column_mapping=column_mapping,
        )


__all__ = ["DataImportService"]
