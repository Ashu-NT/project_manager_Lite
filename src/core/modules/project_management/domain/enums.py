from __future__ import annotations

from enum import Enum


class ProjectStatus(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"


class DependencyType(str, Enum):
    FINISH_TO_START = "FS"
    FINISH_TO_FINISH = "FF"
    START_TO_START = "SS"
    START_TO_FINISH = "SF"


class ConstraintType(str, Enum):
    """A Task scheduling constraint. Values match the existing persisted
    strings (tasks.constraint_type, String(32)) -- do not change them,
    that would silently corrupt any already-stored data."""

    MUST_START_ON = "must_start_on"
    MUST_FINISH_ON = "must_finish_on"
    START_NO_EARLIER_THAN = "start_no_earlier_than"
    START_NO_LATER_THAN = "start_no_later_than"
    FINISH_NO_EARLIER_THAN = "finish_no_earlier_than"
    FINISH_NO_LATER_THAN = "finish_no_later_than"
    DEADLINE = "deadline"


class CostType(str, Enum):
    LABOR = "LABOR"
    MATERIAL = "MATERIAL"
    OVERHEAD = "OVERHEAD"
    EQUIPMENT = "EQUIPMENT"
    CONTINGENCY = "CONTINGENCY"
    SUBCONTRACT = "SUBCONTRACT"
    OTHER = "OTHER"


class WorkerType(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    EXTERNAL = "EXTERNAL"


class ResourceKind(str, Enum):
    PERSON = "PERSON"
    CREW = "CREW"
    EQUIPMENT = "EQUIPMENT"


__all__ = [
    "ProjectStatus",
    "TaskStatus",
    "DependencyType",
    "ConstraintType",
    "CostType",
    "ResourceKind",
    "WorkerType",
]
