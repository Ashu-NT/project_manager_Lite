from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.api.desktop.timesheets.models.entries import (
    TimesheetEntryDesktopDto,
)
from src.core.modules.project_management.api.desktop.timesheets.models.options import (
    TimesheetAssignmentOptionDescriptor,
    TimesheetPeriodOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.timesheets.models.periods import (
    TimesheetPeriodSummaryDesktopDto,
)


@dataclass(frozen=True)
class TimesheetAssignmentSnapshotDesktopDto:
    assignment: TimesheetAssignmentOptionDescriptor
    period_options: tuple[TimesheetPeriodOptionDescriptor, ...]
    selected_period_start: str
    period_summary: TimesheetPeriodSummaryDesktopDto
    entries: tuple[TimesheetEntryDesktopDto, ...]
    resource_period_total_hours_label: str
    scope_summary: str


__all__ = ["TimesheetAssignmentSnapshotDesktopDto"]
