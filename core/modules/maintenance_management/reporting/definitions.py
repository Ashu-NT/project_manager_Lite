from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from src.core.platform.report_runtime import ReportDefinitionRegistry

from .contracts import MAINTENANCE_REPORT_CONTRACTS, MaintenanceReportContract


RenderHandler = Callable[[object], object]


@dataclass(frozen=True)
class CallbackReportDefinition:
    report_key: str
    supported_formats: tuple
    render_handler: RenderHandler
    module_code: str = "maintenance_management"
    permission_code: str = "report.export"

    def render(self, request: object) -> object:
        return self.render_handler(request)


def register_maintenance_management_report_definitions(
    registry: ReportDefinitionRegistry,
    *,
    render_handlers: Mapping[str, RenderHandler],
    contracts: Sequence[MaintenanceReportContract] | None = None,
) -> ReportDefinitionRegistry:
    active_contracts = tuple(contracts or MAINTENANCE_REPORT_CONTRACTS)
    for contract in active_contracts:
        if registry.has(contract.report_key):
            continue
        registry.register(
            CallbackReportDefinition(
                report_key=contract.report_key,
                supported_formats=contract.supported_formats,
                render_handler=render_handlers[contract.report_key],
                permission_code=contract.permission_code,
            )
        )
    return registry


__all__ = [
    "CallbackReportDefinition",
    "register_maintenance_management_report_definitions",
]
