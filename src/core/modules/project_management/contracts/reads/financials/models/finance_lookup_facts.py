from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinanceLookupQuery:
    search: str = ""
    page: int = 1
    page_size: int = 25

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 50))


@dataclass(frozen=True, slots=True)
class FinanceLookupOptionFact:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class FinanceLookupPageFacts:
    items: tuple[FinanceLookupOptionFact, ...]
    total: int
    page: int
    page_size: int

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total


@dataclass(frozen=True, slots=True)
class ManualActualDefaultsFacts:
    project_id: str
    currency_code: str


@dataclass(frozen=True, slots=True)
class ManualActualCostCodeQuery:
    search: str = ""
    page: int = 1
    page_size: int = 25
    effective_on: date | None = None

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 50))


__all__ = [
    "FinanceLookupOptionFact",
    "FinanceLookupPageFacts",
    "FinanceLookupQuery",
    "ManualActualCostCodeQuery",
    "ManualActualDefaultsFacts",
]
