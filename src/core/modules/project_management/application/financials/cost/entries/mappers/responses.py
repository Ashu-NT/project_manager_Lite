from __future__ import annotations

from src.core.modules.project_management.application.financials.cost.entries.approval_result import (
    CostEntryApprovalResult,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.approval import (
    FinancialCostEntryApprovalDto,
)


def map_cost_entry_approval(result: CostEntryApprovalResult) -> FinancialCostEntryApprovalDto:
    return FinancialCostEntryApprovalDto(
        outcome=result.outcome.value, entry_id=result.entry_id, project_id=result.project_id,
        status=result.status.value, row_version=result.row_version,
        approval_request_id=result.approval_request_id or "",
    )
