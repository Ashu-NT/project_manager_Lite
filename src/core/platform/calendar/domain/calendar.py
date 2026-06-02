from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.core.platform.common.ids import generate_id


@dataclass
class WorkingCalendar:
    id: str
    name: str = "Default"
    working_days: set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})
    hours_per_day: float = 8.0

    @staticmethod
    def create_default() -> "WorkingCalendar":
        return WorkingCalendar(id="default", name="Default")


@dataclass
class Holiday:
    id: str
    calendar_id: str
    date: date
    name: str = ""

    @staticmethod
    def create(calendar_id: str, date: date, name: str = "") -> "Holiday":
        return Holiday(
            id=generate_id(),
            calendar_id=calendar_id,
            date=date,
            name=name,
        )


__all__ = ["Holiday", "WorkingCalendar"]
