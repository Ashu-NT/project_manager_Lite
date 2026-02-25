from __future__ import annotations

from typing import Set

from core.models import CalendarEvent, CostItem, CostType, Holiday, WorkingCalendar
from infra.db.models import CalendarEventORM, CostItemORM, HolidayORM, WorkingCalendarORM


def cost_to_orm(cost: CostItem) -> CostItemORM:
    return CostItemORM(
        id=cost.id,
        project_id=cost.project_id,
        task_id=cost.task_id,
        description=cost.description,
        planned_amount=cost.planned_amount,
        actual_amount=cost.actual_amount,
        committed_amount=cost.committed_amount,
        cost_type=(cost.cost_type.value if hasattr(cost.cost_type, "value") else cost.cost_type),
        incurred_date=cost.incurred_date,
        currency_code=cost.currency_code,
        version=getattr(cost, "version", 1),
    )


def cost_from_orm(obj: CostItemORM) -> CostItem:
    return CostItem(
        id=obj.id,
        project_id=obj.project_id,
        task_id=obj.task_id,
        description=obj.description,
        planned_amount=obj.planned_amount,
        committed_amount=obj.committed_amount,
        actual_amount=obj.actual_amount,
        cost_type=CostType(obj.cost_type) if obj.cost_type else CostType.OVERHEAD,
        incurred_date=obj.incurred_date,
        currency_code=obj.currency_code,
        version=getattr(obj, "version", 1),
    )


def event_to_orm(event: CalendarEvent) -> CalendarEventORM:
    return CalendarEventORM(
        id=event.id,
        title=event.title,
        start_date=event.start_date,
        end_date=event.end_date,
        project_id=event.project_id,
        task_id=event.task_id,
        all_day=event.all_day,
        description=event.description,
    )


def event_from_orm(obj: CalendarEventORM) -> CalendarEvent:
    return CalendarEvent(
        id=obj.id,
        title=obj.title,
        start_date=obj.start_date,
        end_date=obj.end_date,
        project_id=obj.project_id,
        task_id=obj.task_id,
        all_day=obj.all_day,
        description=obj.description,
    )


def calendar_from_orm(obj: WorkingCalendarORM) -> WorkingCalendar:
    days: Set[int] = set()
    if obj.working_days:
        for part in obj.working_days.split(","):
            part = part.strip()
            if part:
                days.add(int(part))
    return WorkingCalendar(
        id=obj.id,
        name=obj.name,
        working_days=days,
        hours_per_day=obj.hours_per_day,
    )


def calendar_to_orm(calendar: WorkingCalendar) -> WorkingCalendarORM:
    wd_str = ",".join(str(day) for day in sorted(calendar.working_days))
    return WorkingCalendarORM(
        id=calendar.id,
        name=calendar.name,
        working_days=wd_str,
        hours_per_day=calendar.hours_per_day,
    )


def holiday_from_orm(obj: HolidayORM) -> Holiday:
    return Holiday(
        id=obj.id,
        calendar_id=obj.calendar_id,
        date=obj.date,
        name=obj.name,
    )


def holiday_to_orm(holiday: Holiday) -> HolidayORM:
    return HolidayORM(
        id=holiday.id,
        calendar_id=holiday.calendar_id,
        date=holiday.date,
        name=holiday.name,
    )


__all__ = [
    "cost_to_orm",
    "cost_from_orm",
    "event_to_orm",
    "event_from_orm",
    "calendar_from_orm",
    "calendar_to_orm",
    "holiday_from_orm",
    "holiday_to_orm",
]
