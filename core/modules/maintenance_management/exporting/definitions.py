from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from core.platform.exporting import (
    ExportArtifact,
    ExportArtifactDraft,
    ExportDefinitionRegistry,
)

from .contracts import MAINTENANCE_EXPORT_CONTRACTS, MaintenanceExportContract


ExportHandler = Callable[[object], ExportArtifact | ExportArtifactDraft | Path | str]


@dataclass(frozen=True)
class CallbackExportDefinition:
    operation_key: str
    export_handler: ExportHandler
    module_code: str = "maintenance_management"
    permission_code: str = "report.export"

    def export(self, request: object) -> ExportArtifact | ExportArtifactDraft | Path | str:
        return self.export_handler(request)


def register_maintenance_management_export_definitions(
    registry: ExportDefinitionRegistry,
    *,
    export_handlers: Mapping[str, ExportHandler],
    contracts: Sequence[MaintenanceExportContract] | None = None,
) -> ExportDefinitionRegistry:
    active_contracts = tuple(contracts or MAINTENANCE_EXPORT_CONTRACTS)
    for contract in active_contracts:
        if registry.has(contract.operation_key):
            continue
        registry.register(
            CallbackExportDefinition(
                operation_key=contract.operation_key,
                export_handler=export_handlers[contract.operation_key],
                permission_code=contract.permission_code,
            )
        )
    return registry


__all__ = [
    "CallbackExportDefinition",
    "register_maintenance_management_export_definitions",
]
