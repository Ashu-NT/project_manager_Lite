from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from core.modules.project_management.domain.enums import DependencyType, TaskStatus
from core.modules.project_management.domain.identifiers import generate_id


@dataclass
class Task:
    id: str
    project_id: str
    name: str
    description: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = 0
    percent_complete: float = 0.0
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    deadline: date | None = None
    version: int = 1

    @staticmethod
    def create(project_id: str, name: str, description: str = "", **extra) -> "Task":
        return Task(
            id=generate_id(),
            project_id=project_id,
            name=name,
            description=description,
            **extra,
        )


@dataclass
class TaskAssignment:
    id: str
    task_id: str
    resource_id: str
    allocation_percent: float = 100.0
    hours_logged: float = 0.0
    project_resource_id: Optional[str] = None

    @staticmethod
    def create(
        task_id: str,
        resource_id: str,
        allocation_percent: float = 100.0,
        hours_logged: float = 0.0,
    ) -> "TaskAssignment":
        return TaskAssignment(
            id=generate_id(),
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )


@dataclass
class TaskDependency:
    id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0

    @staticmethod
    def create(
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> "TaskDependency":
        return TaskDependency(
            id=generate_id(),
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )


class TimesheetPeriodStatus(str, Enum):
    OPEN = "OPEN"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"


@dataclass
class TimeEntry:
    id: str
    assignment_id: str
    entry_date: date
    hours: float
    note: str = ""
    author_user_id: str | None = None
    author_username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
        author_user_id: str | None = None,
        author_username: str | None = None,
    ) -> "TimeEntry":
        now = datetime.now(timezone.utc)
        return TimeEntry(
            id=generate_id(),
            assignment_id=assignment_id,
            entry_date=entry_date,
            hours=hours,
            note=note,
            author_user_id=author_user_id,
            author_username=author_username,
            created_at=now,
            updated_at=now,
        )


@dataclass
class TimesheetPeriod:
    id: str
    resource_id: str
    period_start: date
    period_end: date
    status: TimesheetPeriodStatus = TimesheetPeriodStatus.OPEN
    submitted_at: datetime | None = None
    submitted_by_user_id: str | None = None
    submitted_by_username: str | None = None
    decided_at: datetime | None = None
    decided_by_user_id: str | None = None
    decided_by_username: str | None = None
    decision_note: str | None = None
    locked_at: datetime | None = None

    @staticmethod
    def create(
        resource_id: str,
        *,
        period_start: date,
        period_end: date,
    ) -> "TimesheetPeriod":
        return TimesheetPeriod(
            id=generate_id(),
            resource_id=resource_id,
            period_start=period_start,
            period_end=period_end,
        )


__all__ = [
    "Task",
    "TaskAssignment",
    "TaskDependency",
    "TimeEntry",
    "TimesheetPeriod",
    "TimesheetPeriodStatus",
]
