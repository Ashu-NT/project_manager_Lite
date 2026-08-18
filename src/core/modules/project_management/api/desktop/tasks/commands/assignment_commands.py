from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TaskAssignmentCreateCommand:
    task_id: str
    project_resource_id: str
    allocation_percent: float = 100.0
    allocated_planned_hours: Decimal = Decimal("0")


@dataclass(frozen=True)
class TaskAssignmentAllocationCommand:
    assignment_id: str
    allocation_percent: float
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskAssignmentHoursCommand:
    assignment_id: str
    hours_logged: Decimal


@dataclass(frozen=True)
class TaskAssignmentPlannedHoursCommand:
    assignment_id: str
    allocated_planned_hours: Decimal
    expected_assignment_version: int
    expected_project_resource_version: int


__all__ = [
    "TaskAssignmentAllocationCommand",
    "TaskAssignmentCreateCommand",
    "TaskAssignmentHoursCommand",
    "TaskAssignmentPlannedHoursCommand",
]
