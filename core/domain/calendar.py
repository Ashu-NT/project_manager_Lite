from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Set

from core.domain.identifiers import generate_id


@dataclass
class CalendarEvent:
    """A project calendar event optionally linked to project or task."""

    id: str
    title: str
    start_date: date
    end_date: date
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    all_day: bool = True
    description: str = ""

    @staticmethod
    def create(
        title: str,
        start_date: date,
        end_date: date,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        all_day: bool = True,
        description: str = "",
    ) -> "CalendarEvent":
        return CalendarEvent(
            id=generate_id(),
            title=title,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            task_id=task_id,
            all_day=all_day,
            description=description,
        )


@dataclass
class WorkingCalendar:
    id: str
    name: str = "Default"
    working_days: Set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})
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
        return Holiday(id=generate_id(), calendar_id=calendar_id, date=date, name=name)


__all__ = ["CalendarEvent", "WorkingCalendar", "Holiday"]
