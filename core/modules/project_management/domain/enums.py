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


class CostType(str, Enum):
    LABOR = "LABOR"
    MATERIAL = "MATERIAL"
    OVERHEAD = "OVERHEAD"
    EQUIPMENT = "EQUIPMENT"
    CONTINGENCY = "CONTINGENCY"
    SUBCONTRACT = "SUBCONTRACT"
    OTHER = "OTHER"


__all__ = ["ProjectStatus", "TaskStatus", "DependencyType", "CostType"]
