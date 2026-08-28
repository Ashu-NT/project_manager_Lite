from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .finance_budget_facts import FinancePageFacts


_CARD_SORT_KEYS = {"title", "statusLabel", "subtitle", "supportingText", "metaText"}
_LINE_SORT_KEYS = {
    "title",
    "statusLabel",
    "subtitle",
    "supportingText",
    "metaText",
}


@dataclass(frozen=True, slots=True)
class RateCardRequest:
    page: int = 1
    page_size: int = 50
    sort_key: str = "title"
    sort_direction: str = "asc"
    search: str = ""
    scope: str = ""
    status: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _CARD_SORT_KEYS else "title"


@dataclass(frozen=True, slots=True)
class RateLineRequest:
    page: int = 1
    page_size: int = 50
    sort_key: str = "title"
    sort_direction: str = "asc"
    search: str = ""
    rate_type: str = ""
    status: str = ""
    effective_status: str = ""
    as_of: date | None = None

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _LINE_SORT_KEYS else "title"


@dataclass(frozen=True, slots=True)
class RateCardFact:
    id: str
    name: str
    project_id: str | None
    scope: str
    is_active: bool
    version: int
    line_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RateLineFact:
    id: str
    rate_card_id: str
    rate_type: str
    origin: str
    selector_kind: str
    selector_label: str
    resource_id: str | None
    resource_code: str
    resource_name: str
    worker_type: str
    role: str
    skill_code: str
    department_id: str | None
    department_name: str
    customer_party_id: str | None
    contract_reference: str
    effective_from: date | None
    effective_to: date | None
    effective_status: str
    is_active: bool
    unit: str
    rate_amount: Decimal
    rate_currency: str
    overtime_multiplier: Decimal | None
    weekend_multiplier: Decimal | None
    holiday_multiplier: Decimal | None
    version: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class FinanceRateWorkspaceFacts:
    selected_rate_card_id: str
    selected_rate_card: RateCardFact | None
    cards: FinancePageFacts[RateCardFact]
    lines: FinancePageFacts[RateLineFact]


__all__ = [
    "FinanceRateWorkspaceFacts",
    "RateCardFact",
    "RateCardRequest",
    "RateLineFact",
    "RateLineRequest",
]
