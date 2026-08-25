from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.api.desktop.timesheets.models.periods import (
    TimesheetPeriodSummaryDesktopDto,
)


@dataclass(frozen=True)
class TimesheetReviewDetailDesktopDto:
    summary: TimesheetPeriodSummaryDesktopDto


__all__ = [
    "TimesheetReviewDetailDesktopDto",
]
