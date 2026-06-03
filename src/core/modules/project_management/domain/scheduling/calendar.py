from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.core.modules.project_management.domain.identifiers import generate_id


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

__all__ = ["CalendarEvent"]
