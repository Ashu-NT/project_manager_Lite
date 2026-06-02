from __future__ import annotations

from src.core.platform.calendar.domain import Holiday, WorkingCalendar
from src.core.platform.infrastructure.persistence.orm.calendar import HolidayORM, WorkingCalendarORM


def calendar_from_orm(obj: WorkingCalendarORM) -> WorkingCalendar:
    days: set[int] = set()
    if obj.working_days:
        for part in obj.working_days.split(","):
            normalized = part.strip()
            if normalized:
                days.add(int(normalized))
    return WorkingCalendar(
        id=obj.id,
        name=obj.name,
        working_days=days,
        hours_per_day=obj.hours_per_day,
    )


def calendar_to_orm(calendar: WorkingCalendar) -> WorkingCalendarORM:
    working_days = ",".join(str(day) for day in sorted(calendar.working_days))
    return WorkingCalendarORM(
        id=calendar.id,
        name=calendar.name,
        working_days=working_days,
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
    "calendar_from_orm",
    "calendar_to_orm",
    "holiday_from_orm",
    "holiday_to_orm",
]
