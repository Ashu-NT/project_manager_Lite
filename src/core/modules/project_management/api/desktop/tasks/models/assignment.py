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
    allocated_planned_hours: str = "0"
    version: int = 1
    project_resource_version: int = 1
    # Authoritative calendar-based capacity facts for THIS assignment's own
    # current commitment (docs §44's follow-up QML pass) -- reuses the same
    # evaluate_task_assignment_capacity authority the create/edit preview
    # uses, treating this assignment's own allocation_percent as "proposed"
    # against everything else already committed. QML renders these; it does
    # not calculate them.
    capacity_known: bool = False
    capacity_status: str = "UNKNOWN"
    capacity_status_label: str = "Capacity unknown"
    available_capacity_hours_label: str = ""
    committed_capacity_hours_label: str = ""
    capacity_headroom_hours_label: str = ""
    peak_utilization_percent: float = 0.0
    remaining_planned_hours_label: str = "0 h"


__all__ = ["TaskAssignmentDesktopDto"]
