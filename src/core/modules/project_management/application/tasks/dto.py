"""Task use-case commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus


@dataclass(frozen=True)
class TaskCreateCommand:
    project_id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    duration_days: int | None = None
    status: str = TaskStatus.TODO.value
    priority: int | None = None
    deadline: date | None = None
    parent_task_id: str | None = None
    wbs_code: str = ""
    sort_order: int | None = None
    is_milestone: bool = False
    constraint_type: str | None = None
    constraint_date: date | None = None


@dataclass(frozen=True)
class TaskWbsMoveCommand:
    task_id: str
    parent_task_id: str | None
    wbs_code: str | None = None
    sort_order: int | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskUpdateCommand:
    task_id: str
    name: str
    code: str = ""
    description: str = ""
    start_date: date | None = None
    duration_days: int | None = None
    status: str = TaskStatus.TODO.value
    priority: int | None = None
    deadline: date | None = None
    expected_version: int | None = None
    is_milestone: bool | None = None


@dataclass(frozen=True)
class TaskProgressCommand:
    task_id: str
    percent_complete: float | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    status: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskConstraintUpdateCommand:
    """Set/clear a Task's scheduling constraint. constraint_type="" (or
    None) means ASAP -- clears both fields back to no explicit
    constraint. Deliberately separate from TaskUpdateCommand: this is a
    schedule-affecting, governed mutation (see
    TaskSchedulingConstraintHandler), not a generic field edit."""

    task_id: str
    constraint_type: str | None = None
    constraint_date: date | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskAssignmentCreateCommand:
    task_id: str
    project_resource_id: str
    allocation_percent: float = 100.0
    allocated_planned_hours: Decimal = Decimal(0)


@dataclass(frozen=True)
class TaskAssignmentAllocationCommand:
    assignment_id: str
    allocation_percent: float
    expected_version: int


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
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskBulkStatusCommand:
    task_ids: tuple[str, ...]
    status: str
    reopen_percent_complete: float | None = None


__all__ = [
    "TaskAssignmentAllocationCommand",
    "TaskAssignmentCreateCommand",
    "TaskAssignmentHoursCommand",
    "TaskAssignmentPlannedHoursCommand",
    "TaskBulkStatusCommand",
    "TaskConstraintUpdateCommand",
    "TaskCreateCommand",
    "TaskDependencyCreateCommand",
    "TaskDependencyUpdateCommand",
    "TaskProgressCommand",
    "TaskUpdateCommand",
    "TaskWbsMoveCommand",
]
