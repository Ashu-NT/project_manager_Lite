from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.api.desktop.timesheets.models.periods import (
    TimesheetPeriodSummaryDesktopDto,
)


@dataclass(frozen=True)
class TimesheetReviewEntryDesktopDto:
    entry_id: str
    entry_date_label: str
    project_name: str
    task_name: str
    hours_label: str
    author_username: str
    note: str


@dataclass(frozen=True)
class TimesheetReviewDetailDesktopDto:
    summary: TimesheetPeriodSummaryDesktopDto
    entries: tuple[TimesheetReviewEntryDesktopDto, ...]


__all__ = [
    "TimesheetReviewDetailDesktopDto",
    "TimesheetReviewEntryDesktopDto",
]
