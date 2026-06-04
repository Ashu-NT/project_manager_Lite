from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.enums import TaskStatus


@dataclass(frozen=True)
class TaskCreateCommand:
    project_id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    duration_days: int | None = None
    status: str = TaskStatus.TODO.value
    priority: int | None = None
    deadline: date | None = None


@dataclass(frozen=True)
class TaskUpdateCommand:
    task_id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    duration_days: int | None = None
    status: str = TaskStatus.TODO.value
    priority: int | None = None
    deadline: date | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskProgressCommand:
    task_id: str
    percent_complete: float | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    status: str | None = None
    expected_version: int | None = None


__all__ = ["TaskCreateCommand", "TaskProgressCommand", "TaskUpdateCommand"]
