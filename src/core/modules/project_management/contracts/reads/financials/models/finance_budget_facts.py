from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar


_FactT = TypeVar("_FactT")


@dataclass(frozen=True, slots=True)
class FinancePageRequest:
    page: int = 1
    page_size: int = 50
    sort_key: str = ""
    sort_direction: str = "desc"
    search: str = ""
    status: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))


@dataclass(frozen=True, slots=True)
class FinancePageFacts(Generic[_FactT]):
    items: tuple[_FactT, ...]
    total: int
    page: int
    page_size: int
    sort_key: str
    sort_direction: str


@dataclass(frozen=True, slots=True)
class BudgetVersionFact:
    id: str
    name: str
    status: str
    revision: int
    row_version: int
    currency_code: str
    line_count: int
    total_amount: Decimal
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    notes: str


@dataclass(frozen=True, slots=True)
class BudgetLineFact:
    id: str
    budget_id: str
    budget_name: str
    budget_revision: int
    budget_status: str
    description: str
    cost_code: str
    cost_code_name: str
    task_name: str
    wbs_code: str
    amount: Decimal
    currency_code: str


@dataclass(frozen=True, slots=True)
class FinanceBudgetWorkspaceFacts:
    selected_budget_id: str
    versions: FinancePageFacts[BudgetVersionFact]
    lines: FinancePageFacts[BudgetLineFact]


__all__ = [
    "BudgetLineFact",
    "BudgetVersionFact",
    "FinanceBudgetWorkspaceFacts",
    "FinancePageFacts",
    "FinancePageRequest",
]
