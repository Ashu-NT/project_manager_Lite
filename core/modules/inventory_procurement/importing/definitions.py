from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from core.platform.importing import (
    ImportDefinitionRegistry,
    ImportFieldSpec,
    ImportPreview,
    ImportSourceRow,
    ImportSummary,
)


PreviewHandler = Callable[[list[ImportSourceRow]], ImportPreview]
ExecutionHandler = Callable[[list[ImportSourceRow]], ImportSummary]


@dataclass(frozen=True)
class CallbackImportDefinition:
    operation_key: str
    field_specs_value: tuple[ImportFieldSpec, ...]
    preview_handler: PreviewHandler
    execute_handler: ExecutionHandler
    module_code: str = "inventory_procurement"
    permission_code: str = "import.manage"

    def field_specs(self) -> tuple[ImportFieldSpec, ...]:
        return self.field_specs_value

    def preview(self, rows) -> ImportPreview:
        return self.preview_handler(list(rows))

    def execute(self, rows) -> ImportSummary:
        return self.execute_handler(list(rows))


def register_inventory_procurement_import_definitions(
    registry: ImportDefinitionRegistry,
    *,
    schemas: Mapping[str, tuple[ImportFieldSpec, ...]],
    preview_handlers: Mapping[str, PreviewHandler],
    execution_handlers: Mapping[str, ExecutionHandler],
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


__all__ = [
    "CallbackImportDefinition",
    "register_inventory_procurement_import_definitions",
]
