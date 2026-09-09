from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.cost_entries import (
    FinancialCostEntryDto,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
)
from src.core.modules.project_management.application.financials.cost.entries.capabilities import (
    CostEntryActionCapabilities,
    is_manual_actual_entry,
)


def serialize_cost_entry(
    entry: ProjectCostEntry,
    capabilities: CostEntryActionCapabilities | None = None,
) -> FinancialCostEntryDto:
    actions = capabilities or CostEntryActionCapabilities()
    return FinancialCostEntryDto(
        id=entry.id,
        project_id=entry.project_id,
        description=entry.description,
        entry_kind=entry.entry_kind.value,
        status=entry.status.value,
        amount=format_decimal_amount(entry.amount),
        amount_label=format_money(entry.amount, entry.currency_code),
        currency_code=entry.currency_code,
        transaction_date=entry.transaction_date.isoformat(),
        cost_code_id=entry.cost_code_id,
        task_id=entry.task_id or "",
        resource_id=entry.resource_id or "",
        source_label=(
            "Manual entry"
            if entry.source_module.value == "project_management"
            else entry.source_module.value.replace("_", " ").title()
        ),
        source_module=entry.source_module.value,
        source_type=entry.source_type.value,
        source_owned=not is_manual_actual_entry(entry),
        posting_date=entry.posting_date.isoformat() if entry.posting_date else "",
        financial_period_id=entry.financial_period_id or "",
        row_version=entry.row_version,
        can_edit=actions.can_edit,
        can_delete=actions.can_delete,
        can_submit=actions.can_submit,
        can_approve=actions.can_approve,
        can_reject=actions.can_reject,
        can_post=actions.can_post,
        can_reverse=actions.can_reverse,
        approval_action=actions.approval_action,
        read_only_reason=actions.read_only_reason,
    )


__all__ = ["serialize_cost_entry"]
