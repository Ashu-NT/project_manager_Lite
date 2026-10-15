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
