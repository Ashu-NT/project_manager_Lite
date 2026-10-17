"""Map Time-owned work evidence once at the PM application boundary."""

from decimal import Decimal

from src.core.modules.project_management.application.timesheets.dto.responses.time_entries import (
    TimesheetEntryResult,
)
from src.core.platform.domain.time_management.time import TimeEntry


def map_timesheet_entry(entry: TimeEntry) -> TimesheetEntryResult:
    return TimesheetEntryResult(
        entry_id=entry.id,
        assignment_id=entry.assignment_id or entry.work_allocation_id,
        entry_date=entry.entry_date,
        hours=Decimal(str(entry.hours)),
        note=entry.note or "",
        author_user_id=entry.author_user_id,
        author_username=entry.author_username,
        version=entry.version,
    )
