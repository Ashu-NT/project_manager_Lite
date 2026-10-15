from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialAddBudgetLineCommand:
    budget_id: str
    expected_parent_version: int
    cost_code_id: str
    description: str
    amount: str
    currency_code: str
    task_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialUpdateBudgetLineCommand:
    budget_line_id: str
    expected_version: int
    expected_parent_version: int
    cost_code_id: str
    description: str
    amount: str
    currency_code: str
    task_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialDeleteBudgetLineCommand:
    budget_line_id: str
    expected_version: int
    expected_parent_version: int
