from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FinancialPostingFailureDto:
    id: str
    event_id: str
    source_id: str
    source_revision: int
    resource_id: str
    work_date: str
    status: str
    failure_code: str
    failure_message: str
    failure_category: str
    corrective_action: str
    attempt_count: int
    max_attempts: int
    retryable: bool
    updated_at: str


@dataclass(frozen=True, slots=True)
class FinancialPostingFailurePageDto:
    items: tuple[FinancialPostingFailureDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 50
    sort_key: str = "updated"
    sort_direction: str = "desc"
