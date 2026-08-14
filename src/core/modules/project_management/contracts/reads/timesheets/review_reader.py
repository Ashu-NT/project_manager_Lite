from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.platform.application.time_management.time import TimesheetReviewQueueItem
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


@dataclass(frozen=True, slots=True)
class TimesheetReviewCriteria:
    status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED
    search_text: str = ""
    project_id: str | None = None
    resource_id: str | None = None
    period_start_from: date | None = None
    period_start_to: date | None = None
    sort: ReadSort = ReadSort("submittedAt")


@dataclass(frozen=True, slots=True)
class TimesheetReviewReadPage:
    items: tuple[TimesheetReviewQueueItem, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort: ReadSort = ReadSort("submittedAt")


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


__all__ = ["TimesheetReviewCriteria", "TimesheetReviewReadPage", "TimesheetReviewReader"]
