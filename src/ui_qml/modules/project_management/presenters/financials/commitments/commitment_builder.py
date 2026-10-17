from __future__ import annotations

from src.core.modules.project_management.application.financials.commitments.dto.responses.lines import CommitmentPage

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.overview.models.overview_facts import (
    FinanceOverviewFacts,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsCommitmentSummaryViewModel,
    FinancialsRecordViewModel,
)


def build_commitment_summary(
    facts: FinanceOverviewFacts,
) -> FinancialsCommitmentSummaryViewModel:
    has_budget = bool(facts.approved_budget_id)
    rate = facts.control.commitment_rate_percent if has_budget else None
    available = facts.available_after_commitment if has_budget else None
    return FinancialsCommitmentSummaryViewModel(
        approved_budget_label=format_money(facts.approved_budget, facts.currency_code)
        if has_budget
        else "Not budgeted",
        posted_actual_label=format_money(facts.posted_actual, facts.currency_code),
        open_commitment_label=format_money(facts.open_commitment, facts.currency_code),
        available_after_commitment_label="Not budgeted"
        if available is None
        else format_money(available, facts.currency_code),
        commitment_rate_pct=None if rate is None else round(float(rate), 1),
    )


def build_commitment_collection(page: CommitmentPage) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Commitment Ledger",
        subtitle="Procurement-owned commitments synchronized into Project Finance.",
        empty_state="No procurement commitments are linked to this project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=row.id,
                title=f"PO line {row.purchase_order_line_id}",
                status_label=format_money(row.amount, row.currency_code),
                subtitle=row.state.replace("_", " ").title(),
                supporting_text=(
                    f"Matched {format_money(row.matched_amount, row.currency_code)} | Remaining {format_money(row.remaining_amount, row.currency_code)}"
                ),
                meta_text=(row.expected_delivery_date or row.order_date).isoformat()
                if (row.expected_delivery_date or row.order_date)
                else "",
                can_primary_action=False,
                can_secondary_action=False,
                state={
                    "taskId": row.task_id or "",
                    "quantityLabel": f"{row.ordered_quantity} {row.quantity_unit}",
                    "sourceRevision": row.source_revision,
                },
            )
            for row in page.items
        ),
        page=(page.offset // page.limit) + 1 if page.limit else 1,
        page_size=page.limit,
        total=page.total,
    )
