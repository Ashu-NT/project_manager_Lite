from __future__ import annotations

from typing import TypedDict, cast

from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineResponse,
    SchedulingBaselineVarianceRowDto,
)

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
    format_signed_money,
)
from src.core.modules.project_management.contracts.reads.financials.performance.models.performance_facts import (
    CostPhasingFacts,
    PerformanceEvmFact,
    PerformanceVarianceFacts,
)
from src.core.platform.domain.finance.money import canonical_decimal_text
from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _date_label(value) -> str:
    return "Not available" if value is None else value.isoformat()


def _metric_record(
    code,
    label,
    value,
    value_label,
    supporting_text,
    availability="available",
    tone="default",
) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        id=code,
        title=label,
        status_label=value_label,
        subtitle=supporting_text,
        supporting_text="Unavailable"
        if availability != "available"
        else "Authoritative read",
        meta_text=availability.replace("_", " ").title(),
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "value": None if value is None else canonical_decimal_text(value),
            "availability": availability,
            "tone": tone,
        },
    )


def _evm_money_metric(code, label, value, currency, supporting_text):
    return _metric_record(
        code,
        label,
        value,
        "Not available" if value is None else format_money(value, currency),
        supporting_text,
        "unavailable" if value is None else "available",
    )


def _evm_ratio_metric(code, label, value, supporting_text):
    return _metric_record(
        code,
        label,
        value,
        "Not available" if value is None else canonical_decimal_text(value),
        supporting_text,
        "unavailable" if value is None else "available",
    )


def _variance_metric(item):
    return _metric_record(
        item.metric_code,
        item.display_name,
        item.value,
        "Not available"
        if item.value is None
        else format_money(item.value, item.currency_code),
        " | ".join(
            part
            for part in (
                item.semantic_tooltip,
                item.sign_convention,
                item.source_revision,
                item.unavailable_reason,
            )
            if part
        ),
        item.availability,
        {"favorable": "success", "unfavorable": "danger"}.get(
            item.favorability, "default"
        ),
    )


def _metric_collection(
    title: str, subtitle: str, metrics
) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title=title,
        subtitle=subtitle,
        empty_state="No authoritative metrics are available.",
        items=tuple(metrics),
        total=len(metrics),
    )


class FinanceEvmViews(TypedDict):
    evm_basis: FinancialsDetailViewModel
    evm_metrics: FinancialsCollectionViewModel


def build_evm_views(dto: PerformanceEvmFact | None) -> FinanceEvmViews:
    if dto is None:
        return {
            "evm_basis": FinancialsDetailViewModel(
                title="Earned Value Management", status_label="No Data"
            ),
            "evm_metrics": _metric_collection("EVM Metrics", "", ()),
        }
    currency = dto.currency_code
    basis = FinancialsDetailViewModel(
        id=dto.baseline_id or "",
        title="Earned Value Management",
        status_label=dto.availability.replace("_", " ").title(),
        subtitle=(
            dto.unavailable_reason
            or "Canonical Decimal EVM authority at the selected as-of date."
        ),
        description=dto.notes,
        empty_state=dto.unavailable_reason,
        fields=(
            FinancialsDetailFieldViewModel("As of", _date_label(dto.as_of_date)),
            FinancialsDetailFieldViewModel(
                "Currency", dto.currency_code or "Not configured"
            ),
            FinancialsDetailFieldViewModel(
                "Baseline", dto.baseline_id or "Not approved"
            ),
            FinancialsDetailFieldViewModel(
                "Budget revision",
                "Not approved"
                if dto.budget_revision is None
                else f"r{dto.budget_revision}",
            ),
            FinancialsDetailFieldViewModel(
                "Forecast revision",
                "Not approved"
                if dto.forecast_revision is None
                else f"r{dto.forecast_revision}",
                f"Forecast as of {_date_label(dto.forecast_as_of)}",
            ),
            FinancialsDetailFieldViewModel(
                "Calculation precision",
                "Canonical Decimal authority",
                "Money and ratios remain Decimal until a presentation boundary.",
            ),
        ),
        state={"availability": dto.availability},
    )
    return {
        "evm_basis": basis,
        "evm_metrics": _metric_collection(
            "EVM Metrics",
            "BAC/PV/EV/AC and existing derived metrics at the selected as-of date.",
            (
                _evm_money_metric(
                    "bac",
                    "Budget at Completion (BAC)",
                    dto.bac,
                    currency,
                    "Cost-loaded baseline authority.",
                ),
                _evm_money_metric(
                    "pv",
                    "Planned Value (PV)",
                    dto.pv,
                    currency,
                    "Baseline cost by planned completion at the as-of date.",
                ),
                _evm_money_metric(
                    "ev",
                    "Earned Value (EV)",
                    dto.ev,
                    currency,
                    "Baseline cost weighted by authoritative task progress.",
                ),
                _evm_money_metric(
                    "ac",
                    "Actual Cost (AC)",
                    dto.ac,
                    currency,
                    "Canonical posted Project Cost Entry authority.",
                ),
                _evm_ratio_metric(
                    "cpi",
                    "Cost Performance Index (CPI)",
                    dto.cpi,
                    "EV / AC; unavailable when AC is zero.",
                ),
                _evm_ratio_metric(
                    "spi",
                    "Schedule Performance Index (SPI)",
                    dto.spi,
                    "EV / PV; unavailable when PV is zero.",
                ),
                _evm_money_metric(
                    "etc",
                    "Estimate to Complete (ETC)",
                    dto.etc,
                    currency,
                    "Approved Forecast ETC authority.",
                ),
                _evm_money_metric(
                    "eac",
                    "Estimate at Completion (EAC)",
                    dto.eac,
                    currency,
                    "Existing authority: AC + approved Forecast ETC.",
                ),
                _evm_money_metric(
                    "vac",
                    "Variance at Completion (VAC)",
                    dto.vac,
                    currency,
                    "Canonical EVM: BAC - EAC; positive is favorable.",
                ),
                _evm_ratio_metric(
                    "tcpi_bac",
                    "TCPI to BAC",
                    dto.tcpi_bac,
                    "Required cost efficiency to meet BAC.",
                ),
                _evm_ratio_metric(
                    "tcpi_eac",
                    "TCPI to EAC",
                    dto.tcpi_eac,
                    "Required cost efficiency to meet EAC.",
                ),
            ),
        ),
    }


class FinanceVarianceViews(TypedDict):
    variance_metrics: FinancialsCollectionViewModel
    selected_baseline_id: str
    baseline_versions: FinancialsCollectionViewModel
    baseline_variance: tuple[BaselineVarianceRowViewModel, ...]
    variance_basis: FinancialsDetailViewModel


def build_variance_views(dto: PerformanceVarianceFacts | None) -> FinanceVarianceViews:
    if dto is None:
        return {
            "variance_metrics": _metric_collection("Variance Measures", "", ()),
            "selected_baseline_id": "",
            "baseline_versions": FinancialsCollectionViewModel(
                title="Schedule Baseline Versions", subtitle=""
            ),
            "baseline_variance": (),
            "variance_basis": FinancialsDetailViewModel(
                empty_state="Select a schedule baseline to review stored plan movement."
            ),
        }
    baseline_id = dto.selected_baseline_id
    return {
        "variance_metrics": _metric_collection(
            "Variance Measures",
            "Each measure has an authoritative formula, availability reason, and favorability state.",
            tuple(_variance_metric(item) for item in dto.metrics),
        ),
        "selected_baseline_id": baseline_id,
        "baseline_versions": FinancialsCollectionViewModel(
            title="Schedule Baseline Versions",
            subtitle="Stored plan-to-plan movement; this is distinct from EVM schedule variance.",
            empty_state="No approved schedule baselines exist for this project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.name,
                    status_label=item.status.replace("_", " ").title(),
                    subtitle=f"Version {item.version} | Created {item.created_at}",
                    supporting_text=(
                        f"Approved {item.approved_at}"
                        if item.approved_at
                        else "Not approved"
                    ),
                    meta_text="Selected" if item.id == baseline_id else "",
                    state={"selected": item.id == baseline_id},
                )
                for item in cast(tuple[SchedulingBaselineResponse, ...], dto.baseline_versions)
            ),
            total=len(dto.baseline_versions),
        ),
        "baseline_variance": tuple(
            BaselineVarianceRowViewModel(
                task_id=item.task_id,
                task_name=item.task_name,
                start_variance_days=item.start_variance_days,
                finish_variance_days=item.finish_variance_days,
                cost_variance=canonical_decimal_text(item.cost_variance),
                cost_variance_label=format_signed_money(item.cost_variance),
                tone="danger"
                if item.cost_variance > 0
                else "success"
                if item.cost_variance < 0
                else "default",
            )
            for item in cast(tuple[SchedulingBaselineVarianceRowDto, ...], dto.baseline_records)
        ),
        "variance_basis": FinancialsDetailViewModel(
            id=baseline_id,
            title=dto.selected_baseline_label,
            status_label="Stored baseline comparison" if baseline_id else "",
            empty_state="Select a schedule baseline to review stored plan movement.",
            fields=(
                FinancialsDetailFieldViewModel(
                    "Selected baseline", dto.selected_baseline_label
                ),
                FinancialsDetailFieldViewModel(
                    "Compared baseline",
                    dto.compared_baseline_id or "No predecessor comparison",
                ),
                FinancialsDetailFieldViewModel("As of", _date_label(dto.as_of_date)),
                FinancialsDetailFieldViewModel(
                    "Authority",
                    "Plan-to-plan schedule and planned-cost movement",
                    "This is baseline history, not actual-cost performance or EVM schedule variance.",
                ),
            )
            if baseline_id
            else (),
        ),
    }


class FinanceCostPhasingViews(TypedDict):
    cost_phasing: FinancialsCollectionViewModel
    cost_phasing_basis: FinancialsDetailViewModel


def build_cost_phasing_views(dto: CostPhasingFacts | None) -> FinanceCostPhasingViews:
    if dto is None:
        return {
            "cost_phasing": FinancialsCollectionViewModel(
                title="Cost Phasing",
                subtitle="",
                empty_state="No staged cost facts exist in the selected range.",
            ),
            "cost_phasing_basis": FinancialsDetailViewModel(
                title="Cost Phasing Read Basis"
            ),
        }
    return {
        "cost_phasing": FinancialsCollectionViewModel(
            title="Cost Phasing",
            subtitle="Bounded staged project costs. This is not cash receipts, payments, liquidity, AR, or AP.",
            empty_state="No staged cost facts exist in the selected range.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=row.period_key,
                    title=row.period_key,
                    status_label=format_money(row.forecast_cost, row.currency_code),
                    subtitle=f"Planned {format_money(row.planned_cost, row.currency_code)} | Committed {format_money(row.open_commitment, row.currency_code)}",
                    supporting_text=f"Posted actual {format_money(row.posted_actual, row.currency_code)} | Exposure {format_money(row.exposure, row.currency_code)}",
                    meta_text=dto.granularity.title(),
                    can_primary_action=False,
                    can_secondary_action=False,
                    state={
                        "planned": canonical_decimal_text(row.planned_cost),
                        "committed": canonical_decimal_text(row.open_commitment),
                        "actual": canonical_decimal_text(row.posted_actual),
                        "forecast": canonical_decimal_text(row.forecast_cost),
                        "exposure": canonical_decimal_text(row.exposure),
                    },
                )
                for row in dto.periods
            ),
            total=len(dto.periods),
        ),
        "cost_phasing_basis": FinancialsDetailViewModel(
            id=dto.project_id,
            title="Cost Phasing Read Basis",
            status_label=f"{dto.granularity.title()} range",
            fields=(
                FinancialsDetailFieldViewModel(
                    "Range",
                    f"{_date_label(dto.date_from)} to {_date_label(dto.date_to)}",
                ),
                FinancialsDetailFieldViewModel(
                    "Currency", dto.currency_code or "Not configured"
                ),
                FinancialsDetailFieldViewModel(
                    "Budget revision",
                    "Not approved"
                    if dto.approved_budget_revision is None
                    else f"r{dto.approved_budget_revision}",
                ),
                FinancialsDetailFieldViewModel(
                    "Forecast revision",
                    "Not approved"
                    if dto.approved_forecast_revision is None
                    else f"r{dto.approved_forecast_revision}",
                ),
                *tuple(
                    FinancialsDetailFieldViewModel(
                        f"{item.series_code.title()} series",
                        item.availability.replace("_", " ").title(),
                        item.unavailable_reason,
                    )
                    for item in dto.series_availability
                ),
            ),
        ),
    }


class FinanceReportViews(TypedDict):
    report_basis: FinancialsDetailViewModel
    report_definitions: FinancialsCollectionViewModel


def build_reports_views(dto) -> FinanceReportViews:
    return {
        "report_basis": FinancialsDetailViewModel(
            id=dto.project_id,
            title="Project Finance Reports",
            status_label="Authoritative read basis",
            empty_state="No authorized Finance report basis is available.",
            fields=(
                FinancialsDetailFieldViewModel("As of", _date_label(dto.as_of_date)),
                FinancialsDetailFieldViewModel(
                    "Currency", dto.currency_code or "Not configured"
                ),
                FinancialsDetailFieldViewModel(
                    "Budget revision",
                    "Not approved"
                    if dto.budget_revision is None
                    else f"r{dto.budget_revision}",
                ),
                FinancialsDetailFieldViewModel(
                    "Forecast revision",
                    "Not approved"
                    if dto.forecast_revision is None
                    else f"r{dto.forecast_revision}",
                ),
            ),
        ),
        "report_definitions": FinancialsCollectionViewModel(
            title="Available Reports",
            subtitle="Export adapters consume authoritative reads and do not own financial formulas.",
            empty_state="No reports are authorized.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.report_code,
                    title=item.display_name,
                    status_label=" / ".join(value.upper() for value in item.formats),
                    subtitle=item.authority_label,
                    supporting_text="report.view to inspect; report.export plus source permissions to export",
                    meta_text="Read only",
                    can_primary_action=False,
                    can_secondary_action=False,
                )
                for item in dto.definitions
            ),
            total=len(dto.definitions),
        ),
    }


__all__ = [
    "build_cost_phasing_views",
    "build_evm_views",
    "build_reports_views",
    "build_variance_views",
]
