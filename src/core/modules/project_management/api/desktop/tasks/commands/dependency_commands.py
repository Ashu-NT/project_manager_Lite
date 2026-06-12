from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.enums import DependencyType


@dataclass(frozen=True)
class TaskDependencyCreateCommand:
    task_id: str
    linked_task_id: str
    relationship_direction: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


@dataclass(frozen=True)
class TaskDependencyUpdateCommand:
    dependency_id: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


__all__ = ["TaskDependencyCreateCommand", "TaskDependencyUpdateCommand"]
