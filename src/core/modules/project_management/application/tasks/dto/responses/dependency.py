"""Neutral result of a dependency mutation."""

from dataclasses import dataclass

from src.core.modules.project_management.domain.enums import DependencyType


@dataclass(frozen=True)
class TaskDependencyResponseDto:
    id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType
    lag_days: int
    version: int
