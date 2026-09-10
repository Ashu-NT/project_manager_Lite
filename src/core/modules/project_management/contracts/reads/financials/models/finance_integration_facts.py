from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .finance_budget_facts import FinancePageFacts


_SORT_KEYS = {"source", "status", "failure", "attempts", "updated"}
_STATUSES = {"processing", "retry", "quarantined", "dead_letter"}


@dataclass(frozen=True, slots=True)
class ApprovedTimePostingFailureQuery:
    page: int = 1
    page_size: int = 50
    sort_key: str = "updated"
    sort_direction: str = "desc"
    status: str = ""

    @property
    def normalized_page(self) -> int:
        return max(1, int(self.page))

    @property
    def normalized_page_size(self) -> int:
        return max(1, min(int(self.page_size), 200))

    @property
    def normalized_sort_key(self) -> str:
        return self.sort_key if self.sort_key in _SORT_KEYS else "updated"

    @property
    def normalized_status(self) -> str:
        normalized = str(self.status or "").strip().lower()
        return normalized if normalized in _STATUSES else ""


@dataclass(frozen=True, slots=True)
class ApprovedTimePostingFailureFact:
    id: str
    event_id: str
    source_id: str
    source_revision: int
    resource_id: str
    work_date: date | None
    status: str
    failure_code: str
    failure_message: str
    failure_category: str
    corrective_action: str
    attempt_count: int
    max_attempts: int
    retryable: bool
    updated_at: datetime


ApprovedTimePostingFailurePage = FinancePageFacts[ApprovedTimePostingFailureFact]


__all__ = [
    "ApprovedTimePostingFailureFact",
    "ApprovedTimePostingFailurePage",
    "ApprovedTimePostingFailureQuery",
]
