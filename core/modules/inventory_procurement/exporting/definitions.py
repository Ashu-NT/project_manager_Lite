from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from src.core.platform.exporting import (
    ExportArtifact,
    ExportArtifactDraft,
    ExportDefinitionRegistry,
)


ExportHandler = Callable[[object], ExportArtifact | ExportArtifactDraft | Path | str]


@dataclass(frozen=True)
class CallbackExportDefinition:
    operation_key: str
    export_handler: ExportHandler
    module_code: str = "inventory_procurement"
    permission_code: str = "report.export"

    def export(self, request: object) -> ExportArtifact | ExportArtifactDraft | Path | str:
        return self.export_handler(request)


def register_inventory_procurement_export_definitions(
    registry: ExportDefinitionRegistry,
    *,
    export_handlers: Mapping[str, ExportHandler],
    permission_codes: Mapping[str, str] | None = None,
) -> ExportDefinitionRegistry:
    for operation_key, export_handler in export_handlers.items():
        if registry.has(operation_key):
            continue
        registry.register(
            CallbackExportDefinition(
                operation_key=operation_key,
                export_handler=export_handler,
                permission_code=(permission_codes or {}).get(operation_key, "report.export"),
            )
        )
    return registry


__all__ = [
    "CallbackExportDefinition",
    "register_inventory_procurement_export_definitions",
]
