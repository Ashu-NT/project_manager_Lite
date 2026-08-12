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
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)


def serialize_cost_entry(entry: ProjectCostEntry) -> FinancialCostEntryDto:
    is_draft = entry.status is ProjectCostEntryStatus.DRAFT
    # A reversal entry is itself already the correction — the domain
    # (ProjectCostEntry.mark_reversed) forbids reversing a reversal, so the
    # capability flag must agree rather than offer an action the service
    # would reject.
    is_reversible_kind = entry.entry_kind is not ProjectCostEntryKind.REVERSAL
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
        posting_date=entry.posting_date.isoformat() if entry.posting_date else "",
        financial_period_id=entry.financial_period_id or "",
        row_version=entry.row_version,
        can_edit=is_draft,
        can_delete=is_draft,
        can_submit=is_draft,
        can_approve=entry.status is ProjectCostEntryStatus.SUBMITTED,
        can_post=entry.status is ProjectCostEntryStatus.APPROVED,
        can_reverse=entry.status is ProjectCostEntryStatus.POSTED and is_reversible_kind,
    )


__all__ = ["serialize_cost_entry"]
