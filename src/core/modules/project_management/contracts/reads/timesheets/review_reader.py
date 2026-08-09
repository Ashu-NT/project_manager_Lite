from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.platform.application.time_management.time import TimesheetReviewQueueItem
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus


@dataclass(frozen=True, slots=True)
class TimesheetReviewReadPage:
    items: tuple[TimesheetReviewQueueItem, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25


class TimesheetReviewReader(Protocol):
    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        status: TimesheetPeriodStatus | None,
        page: int,
        page_size: int,
    ) -> TimesheetReviewReadPage: ...


__all__ = ["TimesheetReviewReadPage", "TimesheetReviewReader"]
