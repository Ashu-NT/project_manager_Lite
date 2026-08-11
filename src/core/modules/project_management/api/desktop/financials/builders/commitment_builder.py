"""Map canonical application commitment results to desktop DTOs."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.commitments import (
    FinancialCommitmentLineDto,
    FinancialCommitmentSummaryDto,
)
from src.core.modules.project_management.application.financials import ForecastCostService


def build_commitment_line_dto(line) -> FinancialCommitmentLineDto:
    amount = float(line.amount)
    matched = float(line.matched_amount)
    return FinancialCommitmentLineDto(
        id=line.id,
        purchase_order_line_id=line.purchase_order_line_id,
        state=line.state.value,
        amount_label=format_money(amount, line.currency_code),
        matched_amount_label=format_money(matched, line.currency_code),
        remaining_amount_label=format_money(max(0.0, amount - matched), line.currency_code),
        task_id=line.task_id or "",
        quantity_label=f"{line.ordered_quantity} {line.quantity_unit}",
        order_date=line.order_date.isoformat() if line.order_date else "",
        expected_delivery_date=(
            line.expected_delivery_date.isoformat()
            if line.expected_delivery_date
            else ""
        ),
        source_revision=line.source_revision,
    )


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


__all__ = ["build_commitment_line_dto", "build_commitment_summary_dto"]
