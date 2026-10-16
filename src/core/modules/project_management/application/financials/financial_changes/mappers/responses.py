from __future__ import annotations

from src.core.modules.project_management.application.financials.financial_changes.dto.responses.mutations import (
    FinancialChangeMutationDto,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeRequest,
)


def map_change(
    change: FinancialChangeRequest, *, impact: FinancialChangeImpact | None = None,
) -> FinancialChangeMutationDto:
    return FinancialChangeMutationDto(
        change_id=change.id, project_id=change.project_id,
        status=change.status.value, row_version=change.row_version,
        impact_id=impact.id if impact is not None else "",
        impact_row_version=impact.row_version if impact is not None else 0,
        approval_request_id=change.approval_request_id or "",
    )
