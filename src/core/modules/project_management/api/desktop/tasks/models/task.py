from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TaskDesktopDto:
    id: str
    project_id: str
    project_name: str
    name: str
    code: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    priority: int | None
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    deadline: date | None
    version: int


__all__ = ["TaskDesktopDto"]
