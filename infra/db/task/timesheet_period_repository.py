from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import TimesheetPeriodRepository
from core.models import TimesheetPeriod
from infra.db.models import TimesheetPeriodORM
from infra.db.task.timesheet_period_mapper import timesheet_period_from_orm, timesheet_period_to_orm


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


__all__ = ["SqlAlchemyTimesheetPeriodRepository"]
