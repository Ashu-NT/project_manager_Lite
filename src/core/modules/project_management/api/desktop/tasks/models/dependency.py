from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDependencyDesktopDto:
    id: str
    direction: str
    direction_label: str
    linked_task_id: str
    linked_task_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int
    relationship_label: str


__all__ = ["TaskDependencyDesktopDto"]
