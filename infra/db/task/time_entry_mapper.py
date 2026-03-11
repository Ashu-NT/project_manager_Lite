from __future__ import annotations

from core.models import TimeEntry
from infra.db.models import TimeEntryORM


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


__all__ = ["time_entry_to_orm", "time_entry_from_orm"]
