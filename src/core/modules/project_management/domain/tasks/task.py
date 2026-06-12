from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.modules.project_management.domain.identifiers import generate_id


@dataclass
class Task:
    id: str
    project_id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = 0
    percent_complete: float = 0.0
    actual_start: date | None = None
    actual_end: date | None = None
    deadline: date | None = None
    constraint_type: str | None = None
    constraint_date: date | None = None
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
    project_resource_id: str | None = None

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
