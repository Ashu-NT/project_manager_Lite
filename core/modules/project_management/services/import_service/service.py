from __future__ import annotations

from pathlib import Path

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
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._cost_service = cost_service
        self._module_catalog_service = module_catalog_service

    def get_import_schema(self, entity_type: str) -> tuple[ImportFieldSpec, ...]:
        normalized = self._normalize_entity_type(entity_type)
        return self._SCHEMAS[normalized]

    def read_csv_columns(self, file_path: str | Path) -> list[str]:
        columns, _rows = self._load_csv_source(file_path)
        return columns

    def preview_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
        max_rows: int = 100,
    ) -> ImportPreview:
        normalized = self._normalize_entity_type(entity_type)
        columns, rows, mapping = self._prepare_rows(
            normalized,
            file_path,
            column_mapping=column_mapping,
        )
        handlers = {
            "projects": self._preview_projects,
            "resources": self._preview_resources,
            "tasks": self._preview_tasks,
            "costs": self._preview_costs,
        }
        preview = handlers[normalized](rows[: max(1, int(max_rows))])
        preview.entity_type = normalized
        preview.available_columns = columns
        preview.mapped_columns = mapping
        return preview

    def import_csv(
        self,
        entity_type: str,
        file_path: str | Path,
        *,
        column_mapping: dict[str, str | None] | None = None,
    ) -> ImportSummary:
        normalized = self._normalize_entity_type(entity_type)
        _columns, rows, _mapping = self._prepare_rows(
            normalized,
            file_path,
            column_mapping=column_mapping,
        )
        handlers = {
            "projects": self._import_projects,
            "resources": self._import_resources,
            "tasks": self._import_tasks,
            "costs": self._import_costs,
        }
        return handlers[normalized](rows)


__all__ = ["DataImportService"]
