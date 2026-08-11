"""Map canonical application commitment results to desktop DTOs."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.commitments import (
    FinancialCommitmentLineDto,
    FinancialCommitmentSummaryDto,
)


def build_commitment_line_dto(line) -> FinancialCommitmentLineDto:
    amount = float(line.amount)
    matched = float(line.matched_amount)
    return FinancialCommitmentLineDto(
        id=line.id,
        purchase_order_line_id=line.purchase_order_line_id,
        state=line.state.value,
        amount_label=format_money(amount, line.currency_code),
        matched_amount_label=format_money(matched, line.currency_code),
        remaining_amount_label=format_money(line.remaining_money.amount, line.currency_code),
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
    snapshot,
    currency: str | None = None,
) -> FinancialCommitmentSummaryDto:
    budget = float(snapshot.budget)
    actual = float(snapshot.actual)
    committed = float(snapshot.committed)
    available = snapshot.available
    return FinancialCommitmentSummaryDto(
        project_id=project_id,
        approved_budget=budget,
        approved_budget_label=format_money(snapshot.budget, currency),
        posted_actual=actual,
        posted_actual_label=format_money(snapshot.actual, currency),
        open_commitment=committed,
        open_commitment_label=format_money(snapshot.committed, currency),
        available_after_commitment=(None if available is None else float(available)),
        available_after_commitment_label=(
            "Not budgeted" if available is None else format_money(available, currency)
        ),
        commitment_rate_pct=round(float(snapshot.commitment_rate_percent), 1),
    )


__all__ = ["build_commitment_line_dto", "build_commitment_summary_dto"]
