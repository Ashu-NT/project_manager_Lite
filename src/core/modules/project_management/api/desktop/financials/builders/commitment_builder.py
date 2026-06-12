"""Commitment summary DTO assembly.

Delegates to ForecastCostService when available.
Falls back to inline aggregation for backward compatibility.
"""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.commitments import FinancialCommitmentSummaryDto
from src.core.modules.project_management.api.desktop.financials.utils.commitment_utils import commitment_status_value
from src.core.modules.project_management.api.desktop.financials.formatters.money_formatter import format_money


def build_commitment_summary_dto(
    project_id: str,
    *,
    cost_service=None,
    forecast_service=None,
    currency: str | None = None,
) -> FinancialCommitmentSummaryDto:
    """Build FinancialCommitmentSummaryDto.

    Preferred: delegates to ForecastCostService.get_commitment_summary() when injected.
    Fallback: aggregates directly from cost items.
    """
    if forecast_service is not None:
        return _build_from_forecast_service(project_id, forecast_service=forecast_service, currency=currency)
    if cost_service is not None:
        return _build_from_cost_items(project_id, cost_service=cost_service, currency=currency)
    return empty_commitment_summary(project_id, currency)


def _build_from_forecast_service(project_id, *, forecast_service, currency) -> FinancialCommitmentSummaryDto:
    summary = forecast_service.get_commitment_summary(project_id)
    rate_pct = round(
        (summary.committed_total / summary.planned_total * 100.0) if summary.planned_total > 0 else 0.0, 1
    )
    exposure = max(0.0, summary.committed_total - summary.actual_total)
    return FinancialCommitmentSummaryDto(
        project_id=project_id,
        planned_total=summary.planned_total, planned_label=format_money(summary.planned_total, currency),
        uncommitted_total=summary.uncommitted_total, uncommitted_label=format_money(summary.uncommitted_total, currency),
        committed_total=summary.committed_total, committed_label=format_money(summary.committed_total, currency),
        invoiced_total=summary.invoiced_total, invoiced_label=format_money(summary.invoiced_total, currency),
        paid_total=summary.paid_total, paid_label=format_money(summary.paid_total, currency),
        exposure=exposure, exposure_label=format_money(exposure, currency),
        commitment_rate_pct=rate_pct,
    )


def _build_from_cost_items(project_id, *, cost_service, currency) -> FinancialCommitmentSummaryDto:
    items = cost_service.list_cost_items_for_project(project_id)
    uncommitted = sum(getattr(i, "planned_amount", 0.0) or 0.0 for i in items if commitment_status_value(i) == "UNCOMMITTED")
    committed = sum(getattr(i, "committed_amount", 0.0) or 0.0 for i in items if commitment_status_value(i) == "COMMITTED")
    invoiced = sum(getattr(i, "committed_amount", 0.0) or 0.0 for i in items if commitment_status_value(i) == "INVOICED")
    paid = sum(getattr(i, "actual_amount", 0.0) or 0.0 for i in items if commitment_status_value(i) == "PAID")
    planned = sum(getattr(i, "planned_amount", 0.0) or 0.0 for i in items)
    actual = sum(getattr(i, "actual_amount", 0.0) or 0.0 for i in items)
    exposure = max(0.0, committed - actual)
    rate_pct = round((committed / planned * 100.0) if planned > 0 else 0.0, 1)
    return FinancialCommitmentSummaryDto(
        project_id=project_id,
        planned_total=planned, planned_label=format_money(planned, currency),
        uncommitted_total=uncommitted, uncommitted_label=format_money(uncommitted, currency),
        committed_total=committed, committed_label=format_money(committed, currency),
        invoiced_total=invoiced, invoiced_label=format_money(invoiced, currency),
        paid_total=paid, paid_label=format_money(paid, currency),
        exposure=exposure, exposure_label=format_money(exposure, currency),
        commitment_rate_pct=rate_pct,
    )


def empty_commitment_summary(project_id: str, currency: str | None) -> FinancialCommitmentSummaryDto:
    z = format_money(0.0, currency)
    return FinancialCommitmentSummaryDto(
        project_id=project_id,
        planned_total=0.0, planned_label=z,
        uncommitted_total=0.0, uncommitted_label=z,
        committed_total=0.0, committed_label=z,
        invoiced_total=0.0, invoiced_label=z,
        paid_total=0.0, paid_label=z,
        exposure=0.0, exposure_label=z,
        commitment_rate_pct=0.0,
    )


__all__ = ["build_commitment_summary_dto", "empty_commitment_summary"]
