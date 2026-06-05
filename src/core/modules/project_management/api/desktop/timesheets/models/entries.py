from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TimesheetEntryDesktopDto:
    entry_id: str
    assignment_id: str
    entry_date: date
    entry_date_label: str
    hours: float
    hours_label: str
    note: str
    author_username: str


__all__ = ["TimesheetEntryDesktopDto"]
