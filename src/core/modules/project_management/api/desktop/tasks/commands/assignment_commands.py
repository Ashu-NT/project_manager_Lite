from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TaskAssignmentCreateCommand:
    task_id: str
    project_resource_id: str
    allocation_percent: float = 100.0


@dataclass(frozen=True)
class TaskAssignmentAllocationCommand:
    assignment_id: str
    allocation_percent: float


@dataclass(frozen=True)
class TaskAssignmentHoursCommand:
    assignment_id: str
    hours_logged: Decimal


__all__ = [
    "TaskAssignmentAllocationCommand",
    "TaskAssignmentCreateCommand",
    "TaskAssignmentHoursCommand",
]
