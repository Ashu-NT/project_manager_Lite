from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialCreateBudgetVersionCommand:
    project_id: str
    name: str
    currency_code: str = ""


@dataclass(frozen=True, slots=True)
class FinancialCreateBudgetSuccessorCommand:
    predecessor_budget_id: str
    name: str


@dataclass(frozen=True, slots=True)
class FinancialUpdateBudgetCommand:
    budget_id: str
    expected_version: int
    name: str
    notes: str = ""


@dataclass(frozen=True, slots=True)
class FinancialVersionedBudgetCommand:
    budget_id: str
    expected_version: int
    notes: str = ""


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


__all__ = [
    "FinancialAddBudgetLineCommand",
    "FinancialCreateBudgetSuccessorCommand",
    "FinancialCreateBudgetVersionCommand",
    "FinancialDeleteBudgetLineCommand",
    "FinancialUpdateBudgetCommand",
    "FinancialUpdateBudgetLineCommand",
    "FinancialVersionedBudgetCommand",
]
