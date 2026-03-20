from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.platform.importing import (
    ImportDefinitionRegistry,
    ImportFieldSpec,
    ImportPreview,
    ImportSourceRow,
    ImportSummary,
)


PreviewHandler = Callable[[list[tuple[int, dict[str, str]]]], ImportPreview]
ExecutionHandler = Callable[[list[tuple[int, dict[str, str]]]], ImportSummary]


def _as_legacy_rows(rows: list[ImportSourceRow]) -> list[tuple[int, dict[str, str]]]:
    return [(row.line_no, dict(row.values)) for row in rows]


@dataclass(frozen=True)
class CallbackImportDefinition:
    operation_key: str
    field_specs_value: tuple[ImportFieldSpec, ...]
    preview_handler: PreviewHandler
    execute_handler: ExecutionHandler
    module_code: str = "project_management"
    permission_code: str = "import.manage"

    def field_specs(self) -> tuple[ImportFieldSpec, ...]:
        return self.field_specs_value

    def preview(self, rows) -> ImportPreview:
        return self.preview_handler(_as_legacy_rows(list(rows)))

    def execute(self, rows) -> ImportSummary:
        return self.execute_handler(_as_legacy_rows(list(rows)))


def register_project_management_import_definitions(
    registry: ImportDefinitionRegistry,
    *,
    schemas: dict[str, tuple[ImportFieldSpec, ...]],
    preview_handlers: dict[str, PreviewHandler],
    execution_handlers: dict[str, ExecutionHandler],
) -> ImportDefinitionRegistry:
    for operation_key, field_specs in schemas.items():
        if registry.has(operation_key):
            continue
        registry.register(
            CallbackImportDefinition(
                operation_key=operation_key,
                field_specs_value=field_specs,
                preview_handler=preview_handlers[operation_key],
                execute_handler=execution_handlers[operation_key],
            )
        )
    return registry


__all__ = ["register_project_management_import_definitions"]
