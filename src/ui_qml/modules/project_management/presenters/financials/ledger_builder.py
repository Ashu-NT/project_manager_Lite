from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
)

def build_ledger_collection(page) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Ledger Trail",
        subtitle="Canonical manual, Time, and Procurement actual-cost entries.",
        empty_state="No canonical actual-cost entries are available for the selected project.",
        items=tuple(
            FinancialsRecordViewModel(
                id=row.id,
                title=row.description,
                status_label=row.amount_label,
                subtitle=f"{row.source_label} | {row.status.replace('_', ' ').title()}",
                supporting_text=(
                    f"Task {row.task_id}" if row.task_id else "Project-level actual"
                ),
                meta_text=row.posting_date or row.transaction_date,
                can_primary_action=row.can_edit,
                can_secondary_action=row.can_delete,
                can_tertiary_action=row.can_reverse,
                state={
                    "entryId": row.id,
                    "entryKind": row.entry_kind,
                    "status": row.status,
                    "rowVersion": row.row_version,
                    "costCodeId": row.cost_code_id,
                    "taskId": row.task_id,
                    "resourceId": row.resource_id,
                    "transactionDate": row.transaction_date,
                    "postingDate": row.posting_date,
                    "canEdit": row.can_edit,
                    "canDelete": row.can_delete,
                    "canSubmit": row.can_submit,
                    "canApprove": row.can_approve,
                    "canPost": row.can_post,
                    "canReverse": row.can_reverse,
                },
            )
            for row in page.items
        ),
        page=(page.offset // page.limit) + 1 if page.limit else 1,
        page_size=page.limit,
        total=page.total,
    )
