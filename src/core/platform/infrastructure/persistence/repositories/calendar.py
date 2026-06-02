from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.calendar.contracts import WorkingCalendarRepository
from src.core.platform.calendar.domain import Holiday, WorkingCalendar
from src.core.platform.infrastructure.persistence.mappers.calendar import (
    calendar_from_orm,
    holiday_from_orm,
    holiday_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.calendar import HolidayORM, WorkingCalendarORM


class SqlAlchemyWorkingCalendarRepository(WorkingCalendarRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, calendar_id: str) -> WorkingCalendar | None:
        obj = self.session.get(WorkingCalendarORM, calendar_id)
        return calendar_from_orm(obj) if obj else None

    def get_default(self) -> WorkingCalendar | None:
        return self.get("default")

    def upsert(self, calendar: WorkingCalendar) -> None:
        existing = self.session.get(WorkingCalendarORM, calendar.id)
        working_days = ",".join(str(day) for day in sorted(calendar.working_days))
        if existing:
            existing.name = calendar.name
            existing.working_days = working_days
            existing.hours_per_day = calendar.hours_per_day
            return
        self.session.add(
            WorkingCalendarORM(
                id=calendar.id,
                name=calendar.name,
                working_days=working_days,
                hours_per_day=calendar.hours_per_day,
            )
        )

    def list_holidays(self, calendar_id: str) -> list[Holiday]:
        stmt = select(HolidayORM).where(HolidayORM.calendar_id == calendar_id)
        rows = self.session.execute(stmt).scalars().all()
        return [holiday_from_orm(row) for row in rows]

    def add_holiday(self, holiday: Holiday) -> None:
        self.session.add(holiday_to_orm(holiday))

    def delete_holiday(self, holiday_id: str) -> None:
        self.session.query(HolidayORM).filter_by(id=holiday_id).delete()


__all__ = ["SqlAlchemyWorkingCalendarRepository"]
