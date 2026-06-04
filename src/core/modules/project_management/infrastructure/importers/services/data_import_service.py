"""DataImportService — orchestrates domain-specific CSV import operations."""

from __future__ import annotations

from pathlib import Path

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials import CostService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.platform.importing import CsvImportRuntime, ImportDefinitionRegistry

from src.core.modules.project_management.infrastructure.importers.models import (
    ImportFieldSpec,
    ImportPreview,
    ImportSummary,
)
from src.core.modules.project_management.infrastructure.importers.projects.models.project_import_schema import (
    PROJECT_IMPORT_SCHEMA,
)
from src.core.modules.project_management.infrastructure.importers.tasks.models.task_import_schema import (
    TASK_IMPORT_SCHEMA,
)
from src.core.modules.project_management.infrastructure.importers.resources.models.resource_import_schema import (
    RESOURCE_IMPORT_SCHEMA,
)
from src.core.modules.project_management.infrastructure.importers.financials.models.cost_import_schema import (
    COST_IMPORT_SCHEMA,
)
from src.core.modules.project_management.infrastructure.importers.projects.csv.project_csv_importer import (
    import_projects,
    preview_projects,
)
from src.core.modules.project_management.infrastructure.importers.tasks.csv.task_csv_importer import (
    import_tasks,
    preview_tasks,
)
from src.core.modules.project_management.infrastructure.importers.resources.csv.resource_csv_importer import (
    import_resources,
    preview_resources,
)
from src.core.modules.project_management.infrastructure.importers.financials.csv.cost_csv_importer import (
    import_costs,
    preview_costs,
)
from src.core.modules.project_management.infrastructure.importers.services.import_definitions import (
    register_project_management_import_definitions,
)

IMPORT_SCHEMAS: dict[str, tuple[ImportFieldSpec, ...]] = {
    "projects": PROJECT_IMPORT_SCHEMA,
    "resources": RESOURCE_IMPORT_SCHEMA,
    "tasks": TASK_IMPORT_SCHEMA,
    "costs": COST_IMPORT_SCHEMA,
}


class DataImportService(ProjectManagementModuleGuardMixin):
    """
    Orchestrates import operations across PM domains.

    Delegates preview and execute logic to domain-specific importers.
    Does not own PM business logic — it only wires the import pipeline.
    """

    def __init__(
        self,
        *,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        cost_service: CostService,
        user_session=None,
        module_catalog_service=None,
        import_registry: ImportDefinitionRegistry | None = None,
        import_runtime: CsvImportRuntime | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._cost_service = cost_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

        registry = import_registry or ImportDefinitionRegistry()
        register_project_management_import_definitions(
            registry,
            schemas=IMPORT_SCHEMAS,
            preview_handlers={
                "projects": lambda rows: preview_projects(rows, project_service=project_service),
                "resources": lambda rows: preview_resources(rows, resource_service=resource_service),
                "tasks": lambda rows: preview_tasks(rows, project_service=project_service, task_service=task_service),
                "costs": lambda rows: preview_costs(rows, project_service=project_service, task_service=task_service, cost_service=cost_service),
            },
            execution_handlers={
                "projects": lambda rows: import_projects(rows, project_service=project_service),
                "resources": lambda rows: import_resources(rows, resource_service=resource_service),
                "tasks": lambda rows: import_tasks(rows, project_service=project_service, task_service=task_service),
                "costs": lambda rows: import_costs(rows, project_service=project_service, task_service=task_service, cost_service=cost_service),
            },
        )
        self._import_registry = registry
        self._import_runtime = import_runtime or CsvImportRuntime(
            registry,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
        )

    def get_import_schema(self, entity_type: str) -> tuple[ImportFieldSpec, ...]:
        return self._import_runtime.get_import_schema(
            entity_type,
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )

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
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
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
            user_session=self._user_session,
            module_catalog_service=self._module_catalog_service,
        )


__all__ = ["DataImportService", "IMPORT_SCHEMAS"]
