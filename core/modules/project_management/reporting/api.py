"""Reporting API wrappers around renderer classes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from core.modules.project_management.reporting.contexts import ExcelReportContext, PdfReportContext
from core.modules.project_management.reporting.definitions import register_project_management_report_definitions
from core.modules.project_management.reporting.renderers.evm import EvmCurveRenderer
from core.modules.project_management.reporting.renderers.excel import ExcelReportRenderer
from core.modules.project_management.reporting.renderers.gantt import GanttPngRenderer
from core.modules.project_management.reporting.renderers.pdf import PdfReportRenderer
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.reporting.models import GanttTaskBar
from core.platform.common.exceptions import BusinessRuleError
from core.platform.exporting import ExportArtifact, cleanup_temp_artifact, ensure_output_path, finalize_artifact
from src.core.platform.report_runtime import ReportDefinitionRegistry, ReportRuntime


@dataclass(frozen=True)
class GanttPngRequest:
    reporting_service: ReportingService
    project_id: str
    output_path: str | Path
    bars: list[GanttTaskBar] | None = None


@dataclass(frozen=True)
class EvmPngRequest:
    reporting_service: ReportingService
    project_id: str
    output_path: str | Path
    baseline_id: str | None = None
    as_of: date | None = None


@dataclass(frozen=True)
class ExcelReportRequest:
    reporting_service: ReportingService
    project_id: str
    output_path: str | Path
    finance_service: FinanceService | None = None
    baseline_id: str | None = None
    as_of: date | None = None


@dataclass(frozen=True)
class PdfReportRequest:
    reporting_service: ReportingService
    project_id: str
    output_path: str | Path
    temp_dir: str | Path = "tmp_reports"
    finance_service: FinanceService | None = None
    baseline_id: str | None = None
    as_of: date | None = None


_REPORT_RUNTIME: ReportRuntime | None = None


def _optional_report_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except BusinessRuleError as exc:
        if getattr(exc, "code", None) == "NO_BASELINE":
            return None
        raise


def _resolved_as_of(value: date | None) -> date:
    return value or date.today()


def _artifact_path(result: object) -> Path:
    if isinstance(result, ExportArtifact):
        return result.file_path
    return Path(result)


def _resolve_runtime_access_context(
    reporting_service: object,
    *,
    user_session: object | None,
    module_catalog_service: object | None,
) -> tuple[object | None, object | None]:
    return (
        user_session
        if user_session is not None
        else getattr(reporting_service, "_user_session", None),
        module_catalog_service
        if module_catalog_service is not None
        else getattr(reporting_service, "_module_catalog_service", None),
    )


def _build_excel_context(request: ExcelReportRequest) -> ExcelReportContext:
    as_of = _resolved_as_of(request.as_of)
    reporting_service = request.reporting_service
    get_evm = getattr(reporting_service, "get_earned_value", None)
    get_series = getattr(reporting_service, "get_evm_series", None)
    get_variance = getattr(reporting_service, "get_baseline_schedule_variance", None)
    get_cost = getattr(reporting_service, "get_cost_breakdown", None)
    get_cost_sources = getattr(reporting_service, "get_project_cost_source_breakdown", None)
    finance_snapshot = (
        request.finance_service.get_finance_snapshot(request.project_id, as_of=as_of)
        if request.finance_service is not None
        else None
    )
    return ExcelReportContext(
        kpi=reporting_service.get_project_kpis(request.project_id),
        gantt=reporting_service.get_gantt_data(request.project_id),
        resources=reporting_service.get_resource_load_summary(request.project_id),
        evm=(
            _optional_report_call(get_evm, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
            if callable(get_evm)
            else None
        ),
        evm_series=(
            _optional_report_call(get_series, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
            if callable(get_series)
            else None
        ),
        baseline_variance=(
            get_variance(request.project_id, baseline_id=request.baseline_id) if callable(get_variance) else None
        ),
        cost_breakdown=(
            get_cost(request.project_id, as_of=as_of, baseline_id=request.baseline_id) if callable(get_cost) else None
        ),
        cost_sources=(
            get_cost_sources(request.project_id, as_of=as_of) if callable(get_cost_sources) else None
        ),
        finance_snapshot=finance_snapshot,
        as_of=as_of,
    )


def _build_pdf_context(request: PdfReportRequest, gantt_path: Path | None) -> PdfReportContext:
    as_of = _resolved_as_of(request.as_of)
    reporting_service = request.reporting_service
    get_evm = getattr(reporting_service, "get_earned_value", None)
    get_series = getattr(reporting_service, "get_evm_series", None)
    get_variance = getattr(reporting_service, "get_baseline_schedule_variance", None)
    get_cost = getattr(reporting_service, "get_cost_breakdown", None)
    get_cost_sources = getattr(reporting_service, "get_project_cost_source_breakdown", None)
    finance_snapshot = (
        request.finance_service.get_finance_snapshot(request.project_id, as_of=as_of)
        if request.finance_service is not None
        else None
    )
    return PdfReportContext(
        kpi=reporting_service.get_project_kpis(request.project_id),
        gantt_png_path=str(gantt_path) if gantt_path else "",
        resources=reporting_service.get_resource_load_summary(request.project_id),
        evm=(
            _optional_report_call(get_evm, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
            if callable(get_evm)
            else None
        ),
        evm_series=(
            _optional_report_call(get_series, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
            if callable(get_series)
            else None
        ),
        baseline_variance=(
            get_variance(request.project_id, baseline_id=request.baseline_id) if callable(get_variance) else None
        ),
        cost_breakdown=(
            get_cost(request.project_id, as_of=as_of, baseline_id=request.baseline_id) if callable(get_cost) else None
        ),
        cost_sources=(
            get_cost_sources(request.project_id, as_of=as_of) if callable(get_cost_sources) else None
        ),
        finance_snapshot=finance_snapshot,
        as_of=as_of,
    )


def _render_gantt_png(request: object) -> ExportArtifact:
    assert isinstance(request, GanttPngRequest)
    bars = request.bars if request.bars is not None else request.reporting_service.get_gantt_data(request.project_id)
    rendered_path = GanttPngRenderer().render(bars, ensure_output_path(request.output_path))
    return finalize_artifact(rendered_path, media_type="image/png")


def _render_evm_png(request: object) -> ExportArtifact:
    assert isinstance(request, EvmPngRequest)
    output_path = ensure_output_path(request.output_path)
    as_of = _resolved_as_of(request.as_of)
    get_series = getattr(request.reporting_service, "get_evm_series", None)
    if not callable(get_series):
        return finalize_artifact(output_path, media_type="image/png")
    series = _optional_report_call(get_series, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
    if not series:
        return finalize_artifact(output_path, media_type="image/png")
    rendered_path = EvmCurveRenderer().render(series, output_path)
    return finalize_artifact(rendered_path, media_type="image/png")


def _render_excel_report(request: object) -> ExportArtifact:
    assert isinstance(request, ExcelReportRequest)
    ctx = _build_excel_context(request)
    rendered_path = ExcelReportRenderer().render(ctx, ensure_output_path(request.output_path))
    return finalize_artifact(
        rendered_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_pdf_report(request: object) -> ExportArtifact:
    assert isinstance(request, PdfReportRequest)
    output_path = ensure_output_path(request.output_path)
    temp_dir = Path(request.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    gantt_path: Path | None = temp_dir / f"gantt_{request.project_id}.png"
    try:
        try:
            generate_gantt_png(request.reporting_service, request.project_id, gantt_path)
        except ValueError:
            gantt_path = None
        ctx = _build_pdf_context(request, gantt_path)
        rendered_path = PdfReportRenderer().render(ctx, output_path)
        return finalize_artifact(rendered_path, media_type="application/pdf")
    finally:
        cleanup_temp_artifact(gantt_path, temp_dir=temp_dir)


def _get_report_runtime() -> ReportRuntime:
    global _REPORT_RUNTIME
    if _REPORT_RUNTIME is None:
        registry = ReportDefinitionRegistry()
        register_project_management_report_definitions(
            registry,
            render_handlers={
                "gantt_png": _render_gantt_png,
                "evm_png": _render_evm_png,
                "excel_report": _render_excel_report,
                "pdf_report": _render_pdf_report,
            },
        )
        _REPORT_RUNTIME = ReportRuntime(registry)
    return _REPORT_RUNTIME


def generate_gantt_png(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    *,
    bars: list[GanttTaskBar] | None = None,
    user_session: object | None = None,
    module_catalog_service: object | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        reporting_service,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "gantt_png",
            GanttPngRequest(
                reporting_service=reporting_service,
                project_id=project_id,
                output_path=output_path,
                bars=bars,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )


def generate_evm_png(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    baseline_id: str | None = None,
    as_of: date | None = None,
    *,
    user_session: object | None = None,
    module_catalog_service: object | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        reporting_service,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "evm_png",
            EvmPngRequest(
                reporting_service=reporting_service,
                project_id=project_id,
                output_path=output_path,
                baseline_id=baseline_id,
                as_of=as_of,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )


def generate_excel_report(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    finance_service: FinanceService | None = None,
    baseline_id: str | None = None,
    as_of: date | None = None,
    *,
    user_session: object | None = None,
    module_catalog_service: object | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        reporting_service,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "excel_report",
            ExcelReportRequest(
                reporting_service=reporting_service,
                project_id=project_id,
                output_path=output_path,
                finance_service=finance_service,
                baseline_id=baseline_id,
                as_of=as_of,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )


def generate_pdf_report(
    reporting_service: ReportingService,
    project_id: str,
    output_path: str | Path,
    temp_dir: str | Path = "tmp_reports",
    finance_service: FinanceService | None = None,
    baseline_id: str | None = None,
    as_of: date | None = None,
    *,
    user_session: object | None = None,
    module_catalog_service: object | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        reporting_service,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "pdf_report",
            PdfReportRequest(
                reporting_service=reporting_service,
                project_id=project_id,
                output_path=output_path,
                temp_dir=temp_dir,
                finance_service=finance_service,
                baseline_id=baseline_id,
                as_of=as_of,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )
