from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import (
    CalendarEventRepository,
    CostRepository,
    WorkingCalendarRepository,
)
from core.models import CalendarEvent, CostItem, Holiday, WorkingCalendar
from infra.db.cost_calendar.mapper import (
    calendar_from_orm,
    cost_from_orm,
    cost_to_orm,
    event_from_orm,
    event_to_orm,
    holiday_from_orm,
    holiday_to_orm,
)
from infra.db.models import CalendarEventORM, CostItemORM, HolidayORM, WorkingCalendarORM
from infra.db.optimistic import update_with_version_check


class SqlAlchemyCostRepository(CostRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, cost_item: CostItem) -> None:
        self.session.add(cost_to_orm(cost_item))

    def update(self, cost_item: CostItem) -> None:
        cost_item.version = update_with_version_check(
            self.session,
            CostItemORM,
            cost_item.id,
            getattr(cost_item, "version", 1),
            {
                "project_id": cost_item.project_id,
                "task_id": cost_item.task_id,
                "description": cost_item.description,
                "cost_type": (
                    cost_item.cost_type.value
                    if hasattr(cost_item.cost_type, "value")
                    else cost_item.cost_type
                ),
                "currency_code": cost_item.currency_code,
                "planned_amount": cost_item.planned_amount,
                "committed_amount": cost_item.committed_amount,
                "actual_amount": cost_item.actual_amount,
                "incurred_date": cost_item.incurred_date,
            },
            not_found_message="Cost item not found.",
            stale_message="Cost item was updated by another user.",
        )

    def delete(self, cost_id: str) -> None:
        self.session.query(CostItemORM).filter_by(id=cost_id).delete()

    def list_by_project(self, project_id: str) -> List[CostItem]:
        stmt = select(CostItemORM).where(CostItemORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [cost_from_orm(row) for row in rows]

    def delete_by_project(self, project_id: str) -> None:
        self.session.query(CostItemORM).filter_by(project_id=project_id).delete()

    def get(self, cost_id: str) -> Optional[CostItem]:
        obj = self.session.get(CostItemORM, cost_id)
        return cost_from_orm(obj) if obj else None


class SqlAlchemyCalendarEventRepository(CalendarEventRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, event: CalendarEvent) -> None:
        self.session.add(event_to_orm(event))

    def update(self, event: CalendarEvent) -> None:
        self.session.merge(event_to_orm(event))

    def delete(self, event_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(id=event_id).delete()

    def get(self, event_id: str) -> Optional[CalendarEvent]:
        obj = self.session.get(CalendarEventORM, event_id)
        return event_from_orm(obj) if obj else None

    def list_for_project(self, project_id: str) -> List[CalendarEvent]:
        stmt = select(CalendarEventORM).where(CalendarEventORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [event_from_orm(row) for row in rows]

    def list_range(self, start_date: date, end_date: date) -> List[CalendarEvent]:
        stmt = select(CalendarEventORM).where(
            CalendarEventORM.end_date >= start_date,
            CalendarEventORM.start_date <= end_date,
        )
        rows = self.session.execute(stmt).scalars().all()
        return [event_from_orm(row) for row in rows]

    def delete_for_task(self, task_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(task_id=task_id).delete()

    def delete_for_project(self, project_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(project_id=project_id).delete()


class SqlAlchemyWorkingCalendarRepository(WorkingCalendarRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, calendar_id: str) -> Optional[WorkingCalendar]:
        obj = self.session.get(WorkingCalendarORM, calendar_id)
        return calendar_from_orm(obj) if obj else None

    def get_default(self) -> Optional[WorkingCalendar]:
        return self.get("default")

    def upsert(self, calendar: WorkingCalendar) -> None:
        existing = self.session.get(WorkingCalendarORM, calendar.id)
        wd_str = ",".join(str(day) for day in sorted(calendar.working_days))
        if existing:
            existing.name = calendar.name
            existing.working_days = wd_str
            existing.hours_per_day = calendar.hours_per_day
        else:
            self.session.add(
                WorkingCalendarORM(
                    id=calendar.id,
                    name=calendar.name,
                    working_days=wd_str,
                    hours_per_day=calendar.hours_per_day,
                )
            )

    def list_holidays(self, calendar_id: str) -> List[Holiday]:
        stmt = select(HolidayORM).where(HolidayORM.calendar_id == calendar_id)
        rows = self.session.execute(stmt).scalars().all()
        return [holiday_from_orm(row) for row in rows]

    def add_holiday(self, holiday: Holiday) -> None:
        self.session.add(holiday_to_orm(holiday))

    def delete_holiday(self, holiday_id: str) -> None:
        self.session.query(HolidayORM).filter_by(id=holiday_id).delete()


__all__ = [
    "SqlAlchemyCostRepository",
    "SqlAlchemyCalendarEventRepository",
    "SqlAlchemyWorkingCalendarRepository",
]
