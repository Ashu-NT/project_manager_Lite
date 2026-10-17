"""Time-entry write evidence returned by the PM Timesheet use case."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TimesheetEntryResult:
    entry_id: str
    assignment_id: str
    entry_date: date
    hours: Decimal
    note: str
    author_user_id: str | None
    author_username: str | None
    version: int
