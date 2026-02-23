"""Reporting API wrappers around renderer classes."""

from pathlib import Path
from datetime import date
from contextlib import suppress


from core.services.reporting import ReportingService
from core.exceptions import BusinessRuleError
from core.reporting.renderers.gantt import GanttPngRenderer
from core.reporting.renderers.evm import EvmCurveRenderer
from core.reporting.renderers.excel import ExcelReportRenderer
from core.reporting.renderers.pdf import PdfReportRenderer
from core.reporting.contexts import (
    ExcelReportContext,
    PdfReportContext,
)

def _ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _optional_report_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except BusinessRuleError as exc:
        if getattr(exc, "code", None) == "NO_BASELINE":
            return None
        raise


def _cleanup_temp_artifact(path: Path | None, temp_dir: Path | None = None) -> None:
    if path:
        with suppress(FileNotFoundError, PermissionError, OSError):
            path.unlink()

    parent = temp_dir if temp_dir is not None else (path.parent if path else None)
    if parent is None:
        return
    if parent.exists():
        with suppress(FileNotFoundError, PermissionError, OSError):
            if not any(parent.iterdir()):
                parent.rmdir()


def generate_gantt_png(reporting_service: ReportingService, project_id: str, output_path: str | Path) -> Path:
    bars = reporting_service.get_gantt_data(project_id)
    renderer = GanttPngRenderer()
    return renderer.render(bars, _ensure_parent(Path(output_path)))


def generate_evm_png(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    baseline_id: str | None = None,
    as_of: date | None = None,
) -> Path:
    output_path = _ensure_parent(Path(output_path))
    as_of = as_of or date.today()
    get_series = getattr(reporting_service, "get_evm_series", None)
    if not callable(get_series):
        return output_path
    series = _optional_report_call(get_series, project_id, baseline_id=baseline_id, as_of=as_of)
    if not series:
        return output_path
    renderer = EvmCurveRenderer()
    return renderer.render(series, output_path)


def generate_excel_report(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    baseline_id: str | None = None,
    as_of: date | None = None,
) -> Path:
    as_of = as_of or date.today()
    get_evm = getattr(reporting_service, "get_earned_value", None)
    get_series = getattr(reporting_service, "get_evm_series", None)
    get_variance = getattr(reporting_service, "get_baseline_schedule_variance", None)
    get_cost = getattr(reporting_service, "get_cost_breakdown", None)

    ctx = ExcelReportContext(
        kpi=reporting_service.get_project_kpis(project_id),
        gantt=reporting_service.get_gantt_data(project_id),
        resources=reporting_service.get_resource_load_summary(project_id),
        evm=_optional_report_call(get_evm, project_id, baseline_id=baseline_id, as_of=as_of) if callable(get_evm) else None,
        evm_series=_optional_report_call(get_series, project_id, baseline_id=baseline_id, as_of=as_of) if callable(get_series) else None,
        baseline_variance=get_variance(project_id, baseline_id=baseline_id) if callable(get_variance) else None,
        cost_breakdown=get_cost(project_id, as_of=as_of, baseline_id=baseline_id) if callable(get_cost) else None,
        as_of=as_of,
    )
    return ExcelReportRenderer().render(ctx, _ensure_parent(Path(output_path)))


def generate_pdf_report(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    temp_dir: str | Path = "tmp_reports",
    baseline_id: str | None = None,
    as_of: date | None = None,
) -> Path:
    as_of = as_of or date.today()
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    gantt_path = temp_dir / f"gantt_{project_id}.png"
    try:
        generate_gantt_png(reporting_service, project_id, gantt_path)
    except ValueError:
        gantt_path = None

    get_evm = getattr(reporting_service, "get_earned_value", None)
    get_series = getattr(reporting_service, "get_evm_series", None)
    get_variance = getattr(reporting_service, "get_baseline_schedule_variance", None)
    get_cost = getattr(reporting_service, "get_cost_breakdown", None)

    ctx = PdfReportContext(
        kpi=reporting_service.get_project_kpis(project_id),
        gantt_png_path=str(gantt_path) if gantt_path else "",
        resources=reporting_service.get_resource_load_summary(project_id),
        evm=_optional_report_call(get_evm, project_id, baseline_id=baseline_id, as_of=as_of) if callable(get_evm) else None,
        evm_series=_optional_report_call(get_series, project_id, baseline_id=baseline_id, as_of=as_of) if callable(get_series) else None,
        baseline_variance=get_variance(project_id, baseline_id=baseline_id) if callable(get_variance) else None,
        cost_breakdown=get_cost(project_id, as_of=as_of, baseline_id=baseline_id) if callable(get_cost) else None,
        as_of=as_of,
    )
    try:
        return PdfReportRenderer().render(ctx, _ensure_parent(Path(output_path)))
    finally:
        _cleanup_temp_artifact(gantt_path, temp_dir=temp_dir)

