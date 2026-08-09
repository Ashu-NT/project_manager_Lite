from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)


class CostEntryApprovalOutcome(str, Enum):
    APPLIED = "applied"
    PENDING_APPROVAL = "pending_approval"


@dataclass(frozen=True, slots=True)
class CostEntryApprovalResult:
    outcome: CostEntryApprovalOutcome
    entry_id: str
    project_id: str
    status: ProjectCostEntryStatus
    row_version: int
    approval_request_id: str | None = None

    @property
    def is_applied(self) -> bool:
        return self.outcome is CostEntryApprovalOutcome.APPLIED


__all__ = ["CostEntryApprovalOutcome", "CostEntryApprovalResult"]
