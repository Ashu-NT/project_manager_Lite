"""Map canonical application commitment results to desktop DTOs."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.commitments import (
    FinancialCommitmentSummaryDto,
)
from src.core.modules.project_management.application.financials import ForecastCostService


def build_commitment_summary_dto(
    project_id: str,
    *,
    forecast_service: ForecastCostService,
    currency: str | None = None,
) -> FinancialCommitmentSummaryDto:
    summary = forecast_service.get_commitment_summary(project_id)
    rate_percent = round(summary.commitment_rate * 100.0, 1)
    return FinancialCommitmentSummaryDto(
        project_id=project_id,
        planned_total=summary.planned_total,
        planned_label=format_money(summary.planned_total, currency),
        uncommitted_total=summary.uncommitted_total,
        uncommitted_label=format_money(summary.uncommitted_total, currency),
        committed_total=summary.committed_total,
        committed_label=format_money(summary.committed_total, currency),
        invoiced_total=summary.invoiced_total,
        invoiced_label=format_money(summary.invoiced_total, currency),
        paid_total=summary.paid_total,
        paid_label=format_money(summary.paid_total, currency),
        exposure=summary.exposure,
        exposure_label=format_money(summary.exposure, currency),
        commitment_rate_pct=rate_percent,
    )


__all__ = ["build_commitment_summary_dto"]
