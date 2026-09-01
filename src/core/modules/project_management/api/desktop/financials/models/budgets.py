from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialBudgetMutationDto:
    budget_id: str
    project_id: str
    status: str
    row_version: int
    approval_request_id: str = ""


@dataclass(frozen=True, slots=True)
class FinancialBudgetLineMutationDto:
    budget_line_id: str
    budget_id: str
    row_version: int


__all__ = ["FinancialBudgetLineMutationDto", "FinancialBudgetMutationDto"]
