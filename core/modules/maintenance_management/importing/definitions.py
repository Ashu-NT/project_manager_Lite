from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from src.core.platform.importing import (
    ImportDefinitionRegistry,
    ImportPreview,
    ImportSourceRow,
    ImportSummary,
)

from .contracts import MaintenanceWorkbookSheetContract, maintenance_module_import_contracts


PreviewHandler = Callable[[list[ImportSourceRow]], ImportPreview]
ExecutionHandler = Callable[[list[ImportSourceRow]], ImportSummary]


@dataclass(frozen=True)
class CallbackImportDefinition:
    operation_key: str
    field_specs_value: tuple
    preview_handler: PreviewHandler
    execute_handler: ExecutionHandler
    module_code: str = "maintenance_management"
    permission_code: str = "import.manage"

    def field_specs(self) -> tuple:
        return self.field_specs_value

    def preview(self, rows) -> ImportPreview:
        return self.preview_handler(list(rows))

    def execute(self, rows) -> ImportSummary:
        return self.execute_handler(list(rows))


def register_maintenance_management_import_definitions(
    registry: ImportDefinitionRegistry,
    *,
    preview_handlers: Mapping[str, PreviewHandler],
    execution_handlers: Mapping[str, ExecutionHandler],
    contracts: Sequence[MaintenanceWorkbookSheetContract] | None = None,
) -> ImportDefinitionRegistry:
    active_contracts = tuple(contracts or maintenance_module_import_contracts())
    for contract in active_contracts:
        operation_key = contract.operation_key
        if not operation_key or registry.has(operation_key):
            continue
        registry.register(
            CallbackImportDefinition(
                operation_key=operation_key,
                field_specs_value=contract.field_specs,
                preview_handler=preview_handlers[operation_key],
                execute_handler=execution_handlers[operation_key],
            )
        )
    return registry


__all__ = [
    "CallbackImportDefinition",
    "register_maintenance_management_import_definitions",
]
