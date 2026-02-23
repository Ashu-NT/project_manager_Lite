from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from core.domain.enums import DependencyType, TaskStatus
from core.domain.identifiers import generate_id


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


__all__ = ["Task", "TaskAssignment", "TaskDependency"]
