from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.domain.enums import DependencyType


@dataclass(frozen=True, init=False)
class SchedulingDependencyCreateCommand(TaskDependencyCreateCommand):
    """Scheduling vocabulary for the task dependency use case."""

    def __init__(
        self,
        task_id: str,
        related_activity_id: str,
        relationship_direction: str,
        dependency_type: str = DependencyType.FINISH_TO_START.value,
        lag_days: int = 0,
    ) -> None:
        super().__init__(task_id, related_activity_id, relationship_direction, dependency_type, lag_days)

    @property
    def related_activity_id(self) -> str:
        return self.linked_task_id


@dataclass(frozen=True)
class SchedulingDependencyUpdateCommand(TaskDependencyUpdateCommand):
    """Scheduling command accepted directly by the task dependency handler."""
