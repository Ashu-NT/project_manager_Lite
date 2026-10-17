from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.page import (
    CostEntryPage,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)
from src.core.platform.domain.finance.money import canonical_decimal_text
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
)


def _record(row: CostEntryResponse) -> FinancialsRecordViewModel:
    actions = row.capabilities
    source_module = row.source_module.value
    source_label = (
        "Manual entry"
        if source_module == "project_management"
        else source_module.replace("_", " ").title()
    )
    transaction_date = row.transaction_date.isoformat()
    posting_date = row.posting_date.isoformat() if row.posting_date else ""
    return FinancialsRecordViewModel(
        id=row.id,
        title=row.description,
        status_label=format_money(row.amount, row.currency_code),
        subtitle=f"{source_label} | {row.status.value.replace('_', ' ').title()}",
        supporting_text=f"Task {row.task_id}"
        if row.task_id
        else "Project-level actual",
        meta_text=posting_date or transaction_date,
        can_primary_action=actions.can_edit,
        can_secondary_action=actions.can_delete,
        can_tertiary_action=actions.can_reverse,
        state={
            "entryId": row.id,
            "entryKind": row.entry_kind.value,
            "description": row.description,
            "amount": canonical_decimal_text(row.amount),
            "currencyCode": row.currency_code,
            "status": row.status.value,
            "rowVersion": row.row_version,
            "costCodeId": row.cost_code_id,
            "taskId": row.task_id or "",
            "resourceId": row.resource_id or "",
            "sourceModule": source_module,
            "sourceType": row.source_type.value,
            "sourceOwned": not row.is_manual_actual,
            "transactionDate": transaction_date,
            "postingDate": posting_date,
            "canEdit": actions.can_edit,
            "canDelete": actions.can_delete,
            "canSubmit": actions.can_submit,
            "canApprove": actions.can_approve,
            "canReject": actions.can_reject,
            "canPost": actions.can_post,
            "canReverse": actions.can_reverse,
            "approvalAction": actions.approval_action,
            "readOnlyReason": actions.read_only_reason,
        },
    )


def build_ledger_collection(
    page: CostEntryPage,
) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Ledger Trail",
        subtitle="Canonical manual, Time, and Procurement actual-cost entries.",
        empty_state="No canonical actual-cost entries are available for the selected project.",
        items=tuple(_record(row) for row in page.items),
        page=(page.offset // page.limit) + 1 if page.limit else 1,
        page_size=page.limit,
        total=page.total,
    )
