from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.modules.project_management.domain.financials.budget import BudgetStatus


class BudgetApprovalOutcome(str, Enum):
    APPLIED = "applied"
    PENDING_APPROVAL = "pending_approval"


@dataclass(frozen=True, slots=True)
class BudgetApprovalResult:
    outcome: BudgetApprovalOutcome
    budget_id: str
    project_id: str
    budget_status: BudgetStatus
    row_version: int
    approval_request_id: str | None = None

    @property
    def is_applied(self) -> bool:
        return self.outcome is BudgetApprovalOutcome.APPLIED

    @property
    def is_pending_approval(self) -> bool:
        return self.outcome is BudgetApprovalOutcome.PENDING_APPROVAL


__all__ = ["BudgetApprovalOutcome", "BudgetApprovalResult"]
