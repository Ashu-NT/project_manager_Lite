from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from core.platform.time.interfaces import TimeEntryRepository, TimesheetPeriodRepository
from src.infra.persistence.orm.platform.models import TimeEntryORM, TimesheetPeriodORM
from src.infra.persistence.db.platform.time.mapper import (
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

    def get(self, entry_id: str) -> TimeEntry | None:
        obj = self.session.get(TimeEntryORM, entry_id)
        return time_entry_from_orm(obj) if obj else None

    def update(self, entry: TimeEntry) -> None:
        self.session.merge(time_entry_to_orm(entry))

    def delete(self, entry_id: str) -> None:
        self.session.query(TimeEntryORM).filter_by(id=entry_id).delete()

    def list_by_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        stmt = (
            select(TimeEntryORM)
            .where(TimeEntryORM.work_allocation_id == work_allocation_id)
            .order_by(TimeEntryORM.entry_date.asc(), TimeEntryORM.created_at.asc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [time_entry_from_orm(row) for row in rows]

    def delete_by_work_allocation(self, work_allocation_id: str) -> None:
        self.session.query(TimeEntryORM).filter_by(work_allocation_id=work_allocation_id).delete()


class SqlAlchemyTimesheetPeriodRepository(TimesheetPeriodRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, period: TimesheetPeriod) -> None:
        self.session.add(timesheet_period_to_orm(period))

    def get(self, period_id: str) -> TimesheetPeriod | None:
        obj = self.session.get(TimesheetPeriodORM, period_id)
        return timesheet_period_from_orm(obj) if obj else None

    def update(self, period: TimesheetPeriod) -> None:
        self.session.merge(timesheet_period_to_orm(period))

    def get_by_resource_period(self, resource_id: str, period_start: date) -> TimesheetPeriod | None:
        stmt = select(TimesheetPeriodORM).where(
            TimesheetPeriodORM.resource_id == resource_id,
            TimesheetPeriodORM.period_start == period_start,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return timesheet_period_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        stmt = (
            select(TimesheetPeriodORM)
            .where(TimesheetPeriodORM.resource_id == resource_id)
            .order_by(TimesheetPeriodORM.period_start.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [timesheet_period_from_orm(row) for row in rows]

    def list_all(
        self,
        *,
        status: TimesheetPeriodStatus | None = None,
        limit: int | None = None,
    ) -> list[TimesheetPeriod]:
        stmt = select(TimesheetPeriodORM)
        if status is not None:
            stmt = stmt.where(TimesheetPeriodORM.status == status)
        stmt = stmt.order_by(TimesheetPeriodORM.submitted_at.desc(), TimesheetPeriodORM.period_start.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = self.session.execute(stmt).scalars().all()
        return [timesheet_period_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyTimeEntryRepository",
    "SqlAlchemyTimesheetPeriodRepository",
]
