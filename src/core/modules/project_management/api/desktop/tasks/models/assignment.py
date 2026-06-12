from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskAssignmentDesktopDto:
    id: str
    task_id: str
    resource_id: str
    resource_name: str
    allocation_percent: float
    hours_logged: float
    project_resource_id: str | None


__all__ = ["TaskAssignmentDesktopDto"]
