from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAssignmentDesktopDto:
    id: str
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    allocation_percent: float
    hours_logged: float
    allocation_label: str
    hours_label: str


__all__ = ["ResourceAssignmentDesktopDto"]
