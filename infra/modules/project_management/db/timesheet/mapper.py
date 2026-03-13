from __future__ import annotations

from core.platform.common.models import TimeEntry, TimesheetPeriod
from infra.platform.db.models import TimeEntryORM, TimesheetPeriodORM


def time_entry_to_orm(entry: TimeEntry) -> TimeEntryORM:
    return TimeEntryORM(
        id=entry.id,
        assignment_id=entry.assignment_id,
        entry_date=entry.entry_date,
        hours=entry.hours,
        note=entry.note,
        author_user_id=entry.author_user_id,
        author_username=entry.author_username,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def time_entry_from_orm(obj: TimeEntryORM) -> TimeEntry:
    return TimeEntry(
        id=obj.id,
        assignment_id=obj.assignment_id,
        entry_date=obj.entry_date,
        hours=obj.hours,
        note=obj.note,
        author_user_id=obj.author_user_id,
        author_username=obj.author_username,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def timesheet_period_to_orm(period: TimesheetPeriod) -> TimesheetPeriodORM:
    return TimesheetPeriodORM(
        id=period.id,
        resource_id=period.resource_id,
        period_start=period.period_start,
        period_end=period.period_end,
        status=period.status,
        submitted_at=period.submitted_at,
        submitted_by_user_id=period.submitted_by_user_id,
        submitted_by_username=period.submitted_by_username,
        decided_at=period.decided_at,
        decided_by_user_id=period.decided_by_user_id,
        decided_by_username=period.decided_by_username,
        decision_note=period.decision_note,
        locked_at=period.locked_at,
    )


def timesheet_period_from_orm(obj: TimesheetPeriodORM) -> TimesheetPeriod:
    return TimesheetPeriod(
        id=obj.id,
        resource_id=obj.resource_id,
        period_start=obj.period_start,
        period_end=obj.period_end,
        status=obj.status,
        submitted_at=obj.submitted_at,
        submitted_by_user_id=obj.submitted_by_user_id,
        submitted_by_username=obj.submitted_by_username,
        decided_at=obj.decided_at,
        decided_by_user_id=obj.decided_by_user_id,
        decided_by_username=obj.decided_by_username,
        decision_note=obj.decision_note,
        locked_at=obj.locked_at,
    )


__all__ = [
    "time_entry_to_orm",
    "time_entry_from_orm",
    "timesheet_period_to_orm",
    "timesheet_period_from_orm",
]
