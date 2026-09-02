from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .finance_budget_facts import FinancePageFacts

_VERSION_SORT_KEYS = {
    "title", "revision", "statusLabel", "subtitle", "supportingText", "metaText"
}
_LINE_SORT_KEYS = {
    "title", "statusLabel", "subtitle", "supportingText", "metaText", "costCode", "task"
}


@dataclass(frozen=True, slots=True)
class ForecastVersionRequest:
    page: int = 1
    page_size: int = 50
    sort_key: str = "revision"
    sort_direction: str = "desc"
    search: str = ""
    status: str = ""
    generation_mode: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _VERSION_SORT_KEYS else "revision"


@dataclass(frozen=True, slots=True)
class ForecastLineRequest:
    page: int = 1
    page_size: int = 50
    sort_key: str = "title"
    sort_direction: str = "asc"
    search: str = ""
    source_type: str = ""

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
class ForecastVersionFact:
    id: str
    name: str
    status: str
    revision: int
    row_version: int
    currency_code: str
    as_of_date: date
    generation_mode: str
    line_count: int
    total_etc: Decimal
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    notes: str
    approval_request_id: str | None = None
    approval_requested_by_user_id: str | None = None
    can_submit: bool = False
    can_request_approval: bool = False
    can_approve: bool = False
    can_reject: bool = False


@dataclass(frozen=True, slots=True)
class ForecastLineFact:
    id: str
    forecast_id: str
    description: str
    cost_code: str
    cost_code_name: str
    task_name: str
    wbs_code: str
    amount: Decimal
    currency_code: str
    source_kind: str
    source_type: str
    source_reference_type: str
    source_reference_id: str
    source_snapshot_at: datetime | None
    period_start: date | None
    period_end: date | None
    row_version: int


@dataclass(frozen=True, slots=True)
class ForecastVersionPageFacts(FinancePageFacts[ForecastVersionFact]):
    has_open_version: bool = False


@dataclass(frozen=True, slots=True)
class FinanceForecastWorkspaceFacts:
    selected_forecast_id: str
    selected_forecast: ForecastVersionFact | None
    versions: FinancePageFacts[ForecastVersionFact]
    lines: FinancePageFacts[ForecastLineFact]
    show_generate: bool = False
    can_generate: bool = False
    generate_disabled_reason: str = ""


__all__ = [
    "FinanceForecastWorkspaceFacts",
    "ForecastLineFact",
    "ForecastLineRequest",
    "ForecastVersionFact",
    "ForecastVersionPageFacts",
    "ForecastVersionRequest",
]
