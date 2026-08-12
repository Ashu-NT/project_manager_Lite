from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskAssignmentDesktopDto:
    id: str
    task_id: str
    resource_id: str
    resource_name: str
    allocation_percent: float
    hours_logged: str
    project_resource_id: str | None
    response_status: str = "pending"
    response_status_label: str = "Pending"
    can_manage: bool = False
    can_accept: bool = False
    can_decline: bool = False


__all__ = ["TaskAssignmentDesktopDto"]
