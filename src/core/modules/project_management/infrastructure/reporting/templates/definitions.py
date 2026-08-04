from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from src.core.platform.application.data_operations.report_runtime import ReportDefinitionRegistry
from src.core.platform.domain.data_operations.report_runtime import ReportFormat


RenderHandler = Callable[[object], object]


@dataclass(frozen=True)
class CallbackReportDefinition:
    report_key: str
    supported_formats: tuple[ReportFormat, ...]
    render_handler: RenderHandler
    module_code: str = "project_management"
    permission_code: str = "report.export"

    def render(self, request: object) -> object:
        return self.render_handler(request)


def register_project_management_report_definitions(
    registry: ReportDefinitionRegistry,
    *,
    render_handlers: Mapping[str, RenderHandler],
) -> ReportDefinitionRegistry:
    definitions = (
        CallbackReportDefinition("gantt_png", ("png",), render_handlers["gantt_png"]),
        CallbackReportDefinition("evm_png", ("png",), render_handlers["evm_png"]),
        CallbackReportDefinition("excel_report", ("excel",), render_handlers["excel_report"]),
        CallbackReportDefinition("pdf_report", ("pdf",), render_handlers["pdf_report"]),
    )
    for definition in definitions:
        if registry.has(definition.report_key):
            continue
        registry.register(definition)
    return registry


__all__ = ["register_project_management_report_definitions"]
