from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from core.modules.project_management.domain.identifiers import generate_id


class TimesheetPeriodStatus(str, Enum):
    OPEN = "OPEN"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"


@dataclass
class TimeEntry:
    id: str
    assignment_id: str
    entry_date: date
    hours: float
    note: str = ""
    author_user_id: str | None = None
    author_username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
        author_user_id: str | None = None,
        author_username: str | None = None,
    ) -> "TimeEntry":
        now = datetime.now(timezone.utc)
        return TimeEntry(
            id=generate_id(),
            assignment_id=assignment_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
            author_user_id=author_user_id,
            author_username=author_username,
            created_at=now,
            updated_at=now,
        )


@dataclass
class TimesheetPeriod:
    id: str
    resource_id: str
    period_start: date
    period_end: date
    status: TimesheetPeriodStatus = TimesheetPeriodStatus.OPEN
    submitted_at: datetime | None = None
    submitted_by_user_id: str | None = None
    submitted_by_username: str | None = None
    decided_at: datetime | None = None
    decided_by_user_id: str | None = None
    decided_by_username: str | None = None
    decision_note: str | None = None
    locked_at: datetime | None = None

    @staticmethod
    def create(
        resource_id: str,
        *,
        period_start: date,
        period_end: date,
    ) -> "TimesheetPeriod":
        return TimesheetPeriod(
            id=generate_id(),
            resource_id=resource_id,
            period_start=period_start,
            period_end=period_end,
        )


__all__ = [
    "TimeEntry",
    "TimesheetPeriod",
    "TimesheetPeriodStatus",
]
