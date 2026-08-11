from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsCommitmentSummaryViewModel,
    FinancialsRecordViewModel,
)

def build_commitment_summary(summary_dto: Any) -> FinancialsCommitmentSummaryViewModel:
    return FinancialsCommitmentSummaryViewModel(
        planned_label=summary_dto.planned_label,
        uncommitted_label=summary_dto.uncommitted_label,
        committed_label=summary_dto.committed_label,
        invoiced_label=summary_dto.invoiced_label,
        paid_label=summary_dto.paid_label,
        exposure_label=summary_dto.exposure_label,
        commitment_rate_pct=summary_dto.commitment_rate_pct,
    )


def build_commitment_collection(page: Any) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Commitment Ledger",
        subtitle="Procurement-owned commitments synchronized into Project Finance.",
        empty_state="No procurement commitments are linked to this project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=row.id,
                title=f"PO line {row.purchase_order_line_id}",
                status_label=row.amount_label,
                subtitle=row.state.replace("_", " ").title(),
                supporting_text=(
                    f"Matched {row.matched_amount_label} | Remaining {row.remaining_amount_label}"
                ),
                meta_text=row.expected_delivery_date or row.order_date,
                can_primary_action=False,
                can_secondary_action=False,
                state={
                    "taskId": row.task_id,
                    "quantityLabel": row.quantity_label,
                    "sourceRevision": row.source_revision,
                },
            )
            for row in page.items
        ),
        page=(page.offset // page.limit) + 1 if page.limit else 1,
        page_size=page.limit,
        total=page.total,
    )
