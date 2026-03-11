from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import TimeEntryRepository
from core.models import TimeEntry
from infra.db.models import TimeEntryORM
from infra.db.task.time_entry_mapper import time_entry_from_orm, time_entry_to_orm


class SqlAlchemyTimeEntryRepository(TimeEntryRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, entry: TimeEntry) -> None:
        self.session.add(time_entry_to_orm(entry))

    def get(self, entry_id: str) -> Optional[TimeEntry]:
        obj = self.session.get(TimeEntryORM, entry_id)
        return time_entry_from_orm(obj) if obj else None

    def update(self, entry: TimeEntry) -> None:
        self.session.merge(time_entry_to_orm(entry))

    def delete(self, entry_id: str) -> None:
        self.session.query(TimeEntryORM).filter_by(id=entry_id).delete()

    def list_by_assignment(self, assignment_id: str) -> List[TimeEntry]:
        stmt = (
            select(TimeEntryORM)
            .where(TimeEntryORM.assignment_id == assignment_id)
            .order_by(TimeEntryORM.entry_date.asc(), TimeEntryORM.created_at.asc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [time_entry_from_orm(row) for row in rows]

    def delete_by_assignment(self, assignment_id: str) -> None:
        self.session.query(TimeEntryORM).filter_by(assignment_id=assignment_id).delete()


__all__ = ["SqlAlchemyTimeEntryRepository"]
