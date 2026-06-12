from __future__ import annotations

from src.core.modules.project_management.api.desktop.timesheets.formatters.time_formatter import (
    format_hours,
)
from src.core.modules.project_management.api.desktop.timesheets.models.entries import (
    TimesheetEntryDesktopDto,
)


def serialize_entry(entry, assignment_id: str) -> TimesheetEntryDesktopDto:
    return TimesheetEntryDesktopDto(
        entry_id=entry.id,
        assignment_id=assignment_id,
        entry_date=entry.entry_date,
        entry_date_label=entry.entry_date.isoformat(),
        hours=float(entry.hours or 0.0),
        hours_label=format_hours(entry.hours),
        note=entry.note or "",
        author_username=entry.author_username or "unknown",
    )


__all__ = ["serialize_entry"]
