from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.common.interfaces import TimeEntryRepository, TimesheetPeriodRepository
from core.platform.common.models import TimeEntry, TimesheetPeriod
from infra.platform.db.models import TimeEntryORM, TimesheetPeriodORM
from infra.modules.project_management.db.timesheet.mapper import (
    time_entry_from_orm,
    time_entry_to_orm,
    timesheet_period_from_orm,
    timesheet_period_to_orm,
)


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


class SqlAlchemyTimesheetPeriodRepository(TimesheetPeriodRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, period: TimesheetPeriod) -> None:
        self.session.add(timesheet_period_to_orm(period))

    def get(self, period_id: str) -> Optional[TimesheetPeriod]:
        obj = self.session.get(TimesheetPeriodORM, period_id)
        return timesheet_period_from_orm(obj) if obj else None

    def update(self, period: TimesheetPeriod) -> None:
        self.session.merge(timesheet_period_to_orm(period))

    def get_by_resource_period(self, resource_id: str, period_start: date) -> Optional[TimesheetPeriod]:
        stmt = select(TimesheetPeriodORM).where(
            TimesheetPeriodORM.resource_id == resource_id,
            TimesheetPeriodORM.period_start == period_start,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return timesheet_period_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> List[TimesheetPeriod]:
        stmt = (
            select(TimesheetPeriodORM)
            .where(TimesheetPeriodORM.resource_id == resource_id)
            .order_by(TimesheetPeriodORM.period_start.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [timesheet_period_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyTimeEntryRepository",
    "SqlAlchemyTimesheetPeriodRepository",
]
