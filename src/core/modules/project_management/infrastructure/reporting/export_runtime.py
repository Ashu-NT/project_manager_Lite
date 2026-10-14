"""Concrete report rendering runtime used by desktop export adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from src.core.modules.project_management.application.dashboard.models.report_models import (
    GanttTaskBar,
)
from src.core.modules.project_management.application.financials import FinanceService
from src.core.modules.project_management.application.reporting import (
    CostBreakdownReportBuilder,
    EarnedValueReportBuilder,
    ProjectKpiReportBuilder,
    ScheduleVarianceReportBuilder,
)
from src.core.modules.project_management.contracts.reads.financials.models.project_finance_ledger_query import (
    ProjectFinanceLedgerQuery,
)
from src.core.modules.project_management.infrastructure.reporting.exporters.renderers.evm import (
    EvmCurveRenderer,
)
from src.core.modules.project_management.infrastructure.reporting.exporters.renderers.excel import (
    ExcelReportRenderer,
)
from src.core.modules.project_management.infrastructure.reporting.exporters.renderers.gantt import (
    GanttPngRenderer,
)
from src.core.modules.project_management.infrastructure.reporting.exporters.renderers.pdf import (
    PdfReportRenderer,
)
from src.core.modules.project_management.infrastructure.reporting.models.contexts import (
    ExcelReportContext,
    PdfReportContext,
    ProjectFinanceLedgerExportPage,
)
from src.core.modules.project_management.infrastructure.reporting.templates.definitions import (
    register_project_management_report_definitions,
)
from src.core.platform.application.data_operations.exporting import (
    cleanup_temp_artifact,
    ensure_output_path,
    finalize_artifact,
)
from src.core.platform.application.data_operations.report_runtime import (
    ReportDefinitionRegistry,
    ReportRuntime,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.data_operations.exporting import ExportArtifact

if TYPE_CHECKING:
    from src.core.platform.contract.port.tenant.modules import (
        SupportsModuleEntitlements,
    )
    from src.core.platform.domain.security.auth.session import UserSessionContext


@dataclass(frozen=True)
class ProjectReportSources:
    """The report builders a full project report export reads from."""

    kpi: ProjectKpiReportBuilder
    earned_value: EarnedValueReportBuilder | None = None
    schedule_variance: ScheduleVarianceReportBuilder | None = None
    cost_breakdown: CostBreakdownReportBuilder | None = None


@dataclass(frozen=True)
class GanttPngRequest:
    kpi_report: ProjectKpiReportBuilder
    project_id: str
    output_path: str | Path
    bars: list[GanttTaskBar] | None = None


@dataclass(frozen=True)
class EvmPngRequest:
    earned_value_report: EarnedValueReportBuilder
    project_id: str
    output_path: str | Path
    baseline_id: str | None = None
    as_of: date | None = None


@dataclass(frozen=True)
class ExcelReportRequest:
    sources: ProjectReportSources
    project_id: str
    output_path: str | Path
    finance_service: FinanceService | None = None
    baseline_id: str | None = None
    as_of: date | None = None
    finance_period: str = "month"
    project_finance_ledger_offset: int = 0
    project_finance_ledger_limit: int = 500


@dataclass(frozen=True)
class PdfReportRequest:
    sources: ProjectReportSources
    project_id: str
    output_path: str | Path
    temp_dir: str | Path = "tmp_reports"
    finance_service: FinanceService | None = None
    baseline_id: str | None = None
    as_of: date | None = None
    finance_period: str = "month"
    project_finance_ledger_offset: int = 0
    project_finance_ledger_limit: int = 500


_REPORT_RUNTIME: ReportRuntime | None = None


_OPTIONAL_REPORT_CALL_CODES = frozenset({"NO_BASELINE", "PERMISSION_DENIED"})


def _optional_report_call(func, *args, **kwargs):
    """Run a report section builder, degrading to an omitted (None) section
    instead of failing the whole export.
    """
    try:
        return func(*args, **kwargs)
    except BusinessRuleError as exc:
        if getattr(exc, "code", None) in _OPTIONAL_REPORT_CALL_CODES:
            return None
        raise


def _available_evm(value):
    return None if getattr(value, "availability", "available") == "baseline_unavailable" else value


def _resolved_as_of(value: date | None) -> date:
    return value or date.today()  # noqa: DTZ011


def _artifact_path(result: object) -> Path:
    if isinstance(result, ExportArtifact):
        return result.file_path
    # Report definitions render an artifact or a filesystem path.
    return Path(cast("str | Path", result))


def _finance_export_context(request, *, as_of: date):
    ledger_query = ProjectFinanceLedgerQuery(
        offset=request.project_finance_ledger_offset,
        limit=request.project_finance_ledger_limit,
    )
    if request.finance_service is None:
        return None, None
    # A caller without finance.export/finance.read omits the Finance sheet/summary
    # rather than failing the whole export, like the sections below.
    snapshot = _optional_report_call(
        request.finance_service.get_finance_export_snapshot,
        request.project_id,
        as_of=as_of,
        period=request.finance_period,
        ledger_query=ledger_query,
    )
    if snapshot is None:
        return None, None
    return snapshot, ProjectFinanceLedgerExportPage(
        rows=tuple(snapshot.ledger),
        offset=snapshot.ledger_offset,
        limit=snapshot.ledger_limit,
        total=snapshot.ledger_total,
    )


def _resolve_runtime_access_context(
    report_source: object,
    *,
    user_session: UserSessionContext | None,
    module_catalog_service: SupportsModuleEntitlements | None,
) -> tuple[UserSessionContext | None, SupportsModuleEntitlements | None]:
    return (
        user_session
        if user_session is not None
        else getattr(report_source, "_user_session", None),
        module_catalog_service
        if module_catalog_service is not None
        else getattr(report_source, "_module_catalog_service", None),
    )


def _build_excel_context(request: ExcelReportRequest) -> ExcelReportContext:
    as_of = _resolved_as_of(request.as_of)
    sources = request.sources
    get_evm = getattr(sources.earned_value, "get_earned_value", None)
    get_series = getattr(sources.earned_value, "get_evm_series", None)
    get_variance = getattr(sources.schedule_variance, "get_baseline_schedule_variance", None)
    get_cost = getattr(sources.cost_breakdown, "get_cost_breakdown", None)
    get_cost_sources = getattr(sources.cost_breakdown, "get_project_cost_source_breakdown", None)
    finance_snapshot, project_finance_ledger_page = _finance_export_context(
        request,
        as_of=as_of,
    )
    evm = (
        _optional_report_call(get_evm, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
        if callable(get_evm)
        else None
    )
    return ExcelReportContext(
        kpi=sources.kpi.get_project_kpis(request.project_id, as_of=as_of),
        gantt=sources.kpi.get_gantt_data(request.project_id),
        resources=sources.kpi.get_resource_load_summary(request.project_id),
        evm=_available_evm(evm),
        evm_series=(
            _optional_report_call(get_series, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
            if callable(get_series)
            else None
        ),
        baseline_variance=(
            get_variance(request.project_id, baseline_id=request.baseline_id) if callable(get_variance) else None
        ),
        cost_breakdown=(
            _optional_report_call(get_cost, request.project_id, as_of=as_of, baseline_id=request.baseline_id)
            if callable(get_cost)
            else None
        ),
        cost_sources=(
            _optional_report_call(get_cost_sources, request.project_id, as_of=as_of)
            if callable(get_cost_sources)
            else None
        ),
        finance_snapshot=finance_snapshot,
        project_finance_ledger_page=project_finance_ledger_page,
        as_of=as_of,
        generated_at=datetime.now(UTC),
    )


def _build_pdf_context(request: PdfReportRequest, gantt_path: Path | None) -> PdfReportContext:
    as_of = _resolved_as_of(request.as_of)
    sources = request.sources
    get_evm = getattr(sources.earned_value, "get_earned_value", None)
    get_series = getattr(sources.earned_value, "get_evm_series", None)
    get_variance = getattr(sources.schedule_variance, "get_baseline_schedule_variance", None)
    get_cost = getattr(sources.cost_breakdown, "get_cost_breakdown", None)
    get_cost_sources = getattr(sources.cost_breakdown, "get_project_cost_source_breakdown", None)
    finance_snapshot, project_finance_ledger_page = _finance_export_context(
        request,
        as_of=as_of,
    )
    evm = (
        _optional_report_call(get_evm, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
        if callable(get_evm)
        else None
    )
    return PdfReportContext(
        kpi=sources.kpi.get_project_kpis(request.project_id, as_of=as_of),
        gantt_png_path=str(gantt_path) if gantt_path else "",
        resources=sources.kpi.get_resource_load_summary(request.project_id),
        evm=_available_evm(evm),
        evm_series=(
            _optional_report_call(get_series, request.project_id, baseline_id=request.baseline_id, as_of=as_of)
            if callable(get_series)
            else None
        ),
        baseline_variance=(
            get_variance(request.project_id, baseline_id=request.baseline_id) if callable(get_variance) else None
        ),
        cost_breakdown=(
            _optional_report_call(get_cost, request.project_id, as_of=as_of, baseline_id=request.baseline_id)
            if callable(get_cost)
            else None
        ),
        cost_sources=(
            _optional_report_call(get_cost_sources, request.project_id, as_of=as_of)
            if callable(get_cost_sources)
            else None
        ),
        finance_snapshot=finance_snapshot,
        project_finance_ledger_page=project_finance_ledger_page,
        as_of=as_of,
        generated_at=datetime.now(UTC),
    )


def _render_gantt_png(request: object) -> ExportArtifact:
    assert isinstance(request, GanttPngRequest)
    bars = request.bars if request.bars is not None else request.kpi_report.get_gantt_data(request.project_id)
    rendered_path = GanttPngRenderer().render(bars, ensure_output_path(request.output_path))
    return finalize_artifact(rendered_path, media_type="image/png")


def _render_evm_png(request: object) -> ExportArtifact:
    assert isinstance(request, EvmPngRequest)
    output_path = ensure_output_path(request.output_path)
    as_of = _resolved_as_of(request.as_of)
    get_series = getattr(request.earned_value_report, "get_evm_series", None)
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
    gantt_target = temp_dir / f"gantt_{request.project_id}.png"
    gantt_path: Path | None = gantt_target
    try:
        try:
            generate_gantt_png(request.sources.kpi, request.project_id, gantt_target)
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
    kpi_report: ProjectKpiReportBuilder,
    project_id: str,
    output_path: str | Path,
    *,
    bars: list[GanttTaskBar] | None = None,
    user_session: UserSessionContext | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        kpi_report,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "gantt_png",
            GanttPngRequest(
                kpi_report=kpi_report,
                project_id=project_id,
                output_path=output_path,
                bars=bars,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )


def generate_evm_png(
    earned_value_report: EarnedValueReportBuilder,
    project_id: str,
    output_path: str | Path,
    baseline_id: str | None = None,
    as_of: date | None = None,
    *,
    user_session: UserSessionContext | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        earned_value_report,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "evm_png",
            EvmPngRequest(
                earned_value_report=earned_value_report,
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
    sources: ProjectReportSources,
    project_id: str,
    output_path: str | Path,
    finance_service: FinanceService | None = None,
    baseline_id: str | None = None,
    as_of: date | None = None,
    finance_period: str = "month",
    project_finance_ledger_offset: int = 0,
    project_finance_ledger_limit: int = 500,
    *,
    user_session: UserSessionContext | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        sources.kpi,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "excel_report",
            ExcelReportRequest(
                sources=sources,
                project_id=project_id,
                output_path=output_path,
                finance_service=finance_service,
                baseline_id=baseline_id,
                as_of=as_of,
                finance_period=finance_period,
                project_finance_ledger_offset=project_finance_ledger_offset,
                project_finance_ledger_limit=project_finance_ledger_limit,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )


def generate_pdf_report(
    sources: ProjectReportSources,
    project_id: str,
    output_path: str | Path,
    temp_dir: str | Path = "tmp_reports",
    finance_service: FinanceService | None = None,
    baseline_id: str | None = None,
    as_of: date | None = None,
    finance_period: str = "month",
    project_finance_ledger_offset: int = 0,
    project_finance_ledger_limit: int = 500,
    *,
    user_session: UserSessionContext | None = None,
    module_catalog_service: SupportsModuleEntitlements | None = None,
) -> Path:
    resolved_user_session, resolved_module_catalog_service = _resolve_runtime_access_context(
        sources.kpi,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return _artifact_path(
        _get_report_runtime().render(
            "pdf_report",
            PdfReportRequest(
                sources=sources,
                project_id=project_id,
                output_path=output_path,
                temp_dir=temp_dir,
                finance_service=finance_service,
                baseline_id=baseline_id,
                as_of=as_of,
                finance_period=finance_period,
                project_finance_ledger_offset=project_finance_ledger_offset,
                project_finance_ledger_limit=project_finance_ledger_limit,
            ),
            user_session=resolved_user_session,
            module_catalog_service=resolved_module_catalog_service,
        )
    )


__all__ = [
    "ProjectReportSources",
    "generate_evm_png",
    "generate_excel_report",
    "generate_gantt_png",
    "generate_pdf_report",
]
