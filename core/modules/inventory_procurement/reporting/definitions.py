from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from src.core.platform.report_runtime import ReportDefinitionRegistry, ReportFormat


RenderHandler = Callable[[object], object]


@dataclass(frozen=True)
class CallbackReportDefinition:
    report_key: str
    supported_formats: tuple[ReportFormat, ...]
    render_handler: RenderHandler
    module_code: str = "inventory_procurement"
    permission_code: str = "report.export"

    def render(self, request: object) -> object:
        return self.render_handler(request)


def register_inventory_procurement_report_definitions(
    registry: ReportDefinitionRegistry,
    *,
    render_handlers: Mapping[str, RenderHandler],
) -> ReportDefinitionRegistry:
    definitions = (
        CallbackReportDefinition("stock_status_csv", ("csv",), render_handlers["stock_status_csv"]),
        CallbackReportDefinition("stock_status_excel", ("excel",), render_handlers["stock_status_excel"]),
        CallbackReportDefinition(
            "procurement_overview_csv",
            ("csv",),
            render_handlers["procurement_overview_csv"],
        ),
        CallbackReportDefinition(
            "procurement_overview_excel",
            ("excel",),
            render_handlers["procurement_overview_excel"],
        ),
    )
    for definition in definitions:
        if registry.has(definition.report_key):
            continue
        registry.register(definition)
    return registry


__all__ = [
    "CallbackReportDefinition",
    "register_inventory_procurement_report_definitions",
]
