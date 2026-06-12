from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TimesheetEntryCreateCommand:
    assignment_id: str
    entry_date: date
    hours: float
    note: str = ""


@dataclass(frozen=True)
class TimesheetEntryUpdateCommand:
    entry_id: str
    entry_date: date | None = None
    hours: float | None = None
    note: str | None = None


__all__ = ["TimesheetEntryCreateCommand", "TimesheetEntryUpdateCommand"]
