from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TimesheetPeriodSummaryDesktopDto:
    period_id: str
    resource_id: str
    resource_name: str
    period_start: date
    period_start_label: str
    period_end_label: str
    status: str
    status_label: str
    submitted_by_username: str
    submitted_at_label: str
    decided_by_username: str
    decided_at_label: str
    decision_note: str
    entry_count: int
    total_hours: float
    total_hours_label: str
    project_names: tuple[str, ...]
    version: int = 1
    project_count: int = 0
    task_count: int = 0
    generic_entry_count: int = 0
    can_approve: bool = False
    can_reject: bool = False
    can_lock: bool = False
    can_unlock: bool = False


@dataclass(frozen=True)
class TimesheetReviewPageDesktopDto:
    items: tuple[TimesheetPeriodSummaryDesktopDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "submittedAt"
    sort_direction: str = "desc"


__all__ = ["TimesheetPeriodSummaryDesktopDto", "TimesheetReviewPageDesktopDto"]
