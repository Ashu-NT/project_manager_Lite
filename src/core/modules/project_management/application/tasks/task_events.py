from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCreated:
    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskProfileUpdated:
    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    occurred_at: datetime


class TaskHierarchyChangeType(str, Enum):
    MOVED = "MOVED"
    RECODED = "RECODED"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskHierarchyChanged:
    """`move_task`/`recode_task` -- includes sibling resequencing under the same
    project_id target; siblings are not individually faceted, matching how the
    legacy signal only ever carried project_id."""

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    change_type: TaskHierarchyChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskStatusChanged:
    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    old_status: str
    new_status: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskProgressChanged:
    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    percent_complete: float
    occurred_at: datetime


class TaskScheduleChangeType(str, Enum):
    CONSTRAINT_UPDATED = "CONSTRAINT_UPDATED"
    LEVELING_APPLIED = "LEVELING_APPLIED"
    APPROVED_SCHEDULE_APPLIED = "APPROVED_SCHEDULE_APPLIED"
    CASCADE_RECALCULATED = "CASCADE_RECALCULATED"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskScheduleChanged:
    """One instance per actually-changed Task -- never a synthetic project-level
    bulk fact (P45A-FINAL-CLOSURE §8/§41). ViewInvalidation dedupes UI amplification
    by correlation_id + target identity; DomainEvent volume mirrors real mutation
    volume 1:1."""

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    change_type: TaskScheduleChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskRemoved:
    """One instance per actually-deleted Task -- direct delete, bulk delete, and
    Project cascade-delete all record this per task_id (P45A-FINAL-CLOSURE §9)."""

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    occurred_at: datetime


class TaskAssignmentChangeType(str, Enum):
    ASSIGNED = "ASSIGNED"
    UNASSIGNED = "UNASSIGNED"
    HOURS_CHANGED = "HOURS_CHANGED"
    ALLOCATION_CHANGED = "ALLOCATION_CHANGED"
    PLANNED_HOURS_CHANGED = "PLANNED_HOURS_CHANGED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    HOURS_LOGGED_CHANGED = "HOURS_LOGGED_CHANGED"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskAssignmentChanged:
    """HOURS_CHANGED (manual `set_assignment_hours`) and HOURS_LOGGED_CHANGED (the
    TimeEntry-driven sync) are deliberately distinct change_types, not merged --
    production treats them as mutually exclusive alternate paths to the same
    field with different provenance (P45A-FINAL-CLOSURE §11)."""

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    assignment_id: str
    resource_id: str
    change_type: TaskAssignmentChangeType
    occurred_at: datetime


class TaskDependencyChangeType(str, Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDependencyChanged:
    tenant_id: str
    organization_id: str
    project_id: str
    dependency_id: str
    predecessor_task_id: str
    successor_task_id: str
    change_type: TaskDependencyChangeType
    occurred_at: datetime


__all__ = [
    "TaskCreated",
    "TaskProfileUpdated",
    "TaskHierarchyChangeType",
    "TaskHierarchyChanged",
    "TaskStatusChanged",
    "TaskProgressChanged",
    "TaskScheduleChangeType",
    "TaskScheduleChanged",
    "TaskRemoved",
    "TaskAssignmentChangeType",
    "TaskAssignmentChanged",
    "TaskDependencyChangeType",
    "TaskDependencyChanged",
]
