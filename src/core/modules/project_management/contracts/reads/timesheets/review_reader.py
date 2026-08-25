from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Protocol

from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


class ReviewQueueItemType(str, Enum):
    TIMESHEET_PERIOD = "TIMESHEET_PERIOD"


@dataclass(frozen=True, slots=True)
class TimesheetReviewCriteria:
    item_id: str | None = None
    status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED
    search_text: str = ""
    project_id: str | None = None
    resource_id: str | None = None
    period_start_from: date | None = None
    period_start_to: date | None = None
    sort: ReadSort = ReadSort("submittedAt", ReadSortDirection.DESCENDING)


@dataclass(frozen=True, slots=True)
class TimesheetReviewQueueFact:
    item_id: str
    timesheet_period_id: str
    version: int
    resource_id: str
    resource_name: str
    resource_code: str
    period_start: date
    period_end: date
    status: TimesheetPeriodStatus
    submitted_at: datetime | None
    submitted_by_username: str | None
    decided_at: datetime | None
    decided_by_username: str | None
    decision_note: str | None
    total_hours: float
    project_count: int
    task_count: int
    entry_count: int
    generic_entry_count: int
    project_ids: tuple[str, ...]
    item_type: ReviewQueueItemType = ReviewQueueItemType.TIMESHEET_PERIOD
    can_approve: bool = False
    can_reject: bool = False
    can_lock: bool = False
    can_unlock: bool = False

    @property
    def period_id(self) -> str:
        return self.timesheet_period_id


@dataclass(frozen=True, slots=True)
class TimesheetReviewInspectorFact:
    summary: TimesheetReviewQueueFact


@dataclass(frozen=True, slots=True)
class TimesheetReviewReadPage:
    items: tuple[TimesheetReviewQueueFact, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("submittedAt", ReadSortDirection.DESCENDING)


class TimesheetReviewReader(Protocol):
    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: TimesheetReviewCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetReviewReadPage: ...


class TimesheetReviewInspectorReader(Protocol):
    def read_item(
        self,
        *,
        item_id: str,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
    ) -> TimesheetReviewInspectorFact | None: ...


__all__ = [
    "ReviewQueueItemType",
    "TimesheetReviewCriteria",
    "TimesheetReviewInspectorFact",
    "TimesheetReviewInspectorReader",
    "TimesheetReviewQueueFact",
    "TimesheetReviewReadPage",
    "TimesheetReviewReader",
]
