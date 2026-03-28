from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from core.platform.common.ids import generate_id


class TimesheetPeriodStatus(str, Enum):
    OPEN = "OPEN"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"


@dataclass
class TimeEntry:
    id: str
    work_allocation_id: str
    entry_date: date
    hours: float
    assignment_id: str | None = None
    note: str = ""
    author_user_id: str | None = None
    author_username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    owner_type: str = "work_allocation"
    owner_id: str | None = None
    owner_label: str = ""
    scope_type: str | None = None
    scope_id: str | None = None
    employee_id: str | None = None
    department_id: str | None = None
    department_name: str = ""
    site_id: str | None = None
    site_name: str = ""

    @staticmethod
    def create(
        work_allocation_id: str,
        *,
        entry_date: date,
        hours: float,
        assignment_id: str | None = None,
        note: str = "",
        author_user_id: str | None = None,
        author_username: str | None = None,
        owner_type: str = "work_allocation",
        owner_id: str | None = None,
        owner_label: str = "",
        scope_type: str | None = None,
        scope_id: str | None = None,
        employee_id: str | None = None,
        department_id: str | None = None,
        department_name: str = "",
        site_id: str | None = None,
        site_name: str = "",
    ) -> "TimeEntry":
        now = datetime.now(timezone.utc)
        normalized_work_allocation_id = (work_allocation_id or "").strip()
        normalized_owner_type = (owner_type or "work_allocation").strip() or "work_allocation"
        normalized_assignment_id = (assignment_id or "").strip() or None
        if normalized_assignment_id is None and normalized_owner_type == "task_assignment":
            normalized_assignment_id = normalized_work_allocation_id
        return TimeEntry(
            id=generate_id(),
            work_allocation_id=normalized_work_allocation_id,
            entry_date=entry_date,
            hours=hours,
            assignment_id=normalized_assignment_id,
            note=note,
            author_user_id=author_user_id,
            author_username=author_username,
            created_at=now,
            updated_at=now,
            owner_type=normalized_owner_type,
            owner_id=owner_id or normalized_assignment_id or normalized_work_allocation_id,
            owner_label=(owner_label or "").strip(),
            scope_type=(scope_type or "").strip() or None,
            scope_id=(scope_id or "").strip() or None,
            employee_id=employee_id,
            department_id=department_id,
            department_name=(department_name or "").strip(),
            site_id=site_id,
            site_name=(site_name or "").strip(),
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


WorkEntry = TimeEntry


__all__ = [
    "TimeEntry",
    "WorkEntry",
    "TimesheetPeriod",
    "TimesheetPeriodStatus",
]
