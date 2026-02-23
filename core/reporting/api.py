""" TODO: future developpment
    Refactor the exporter.py
"""

from pathlib import Path
from datetime import date


from core.services.reporting import ReportingService
from core.reporting.renderers.gantt import GanttPngRenderer
from core.reporting.renderers.evm import EvmCurveRenderer
from core.reporting.renderers.excel import ExcelReportRenderer
from core.reporting.renderers.pdf import PdfReportRenderer
from core.reporting.contexts import (
    ExcelReportContext,
    PdfReportContext,
)


def generate_gantt_png(reporting_service: ReportingService, project_id: str, output_path: str | Path) -> Path:
    bars = reporting_service.get_gantt_data(project_id)
    renderer = GanttPngRenderer()
    return renderer.render(bars, Path(output_path))


def generate_evm_png(reporting_service: ReportingService, project_id: str, output_path: str | Path) -> Path:
    series = reporting_service.get_evm_series(project_id)
    if not series:
        return Path(output_path)
    renderer = EvmCurveRenderer()
    return renderer.render(series, Path(output_path))


def generate_excel_report(reporting_service: ReportingService, project_id: str, output_path: str | Path) -> Path:
    ctx = ExcelReportContext(
        kpi=reporting_service.get_project_kpis(project_id),
        gantt=reporting_service.get_gantt_data(project_id),
        resources=reporting_service.get_resource_load_summary(project_id),
        evm=getattr(reporting_service, "get_earned_value", lambda *_: None)(project_id),
        evm_series=getattr(reporting_service, "get_evm_series", lambda *_: None)(project_id),
        baseline_variance=None,
        cost_breakdown=None,
        as_of=date.today(),
    )
    return ExcelReportRenderer().render(ctx, Path(output_path))


def generate_pdf_report(reporting_service: ReportingService, project_id: str, output_path: str | Path) -> Path:
    gantt_path = Path("tmp_reports") / f"gantt_{project_id}.png"
    generate_gantt_png(reporting_service, project_id, gantt_path)

    ctx = PdfReportContext(
        kpi=reporting_service.get_project_kpis(project_id),
        gantt_png_path=str(gantt_path),
        resources=reporting_service.get_resource_load_summary(project_id),
        evm=None,
        evm_series=None,
        baseline_variance=None,
        cost_breakdown=None,
        as_of=date.today(),
    )
    return PdfReportRenderer().render(ctx, Path(output_path))

