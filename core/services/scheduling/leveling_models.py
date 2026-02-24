from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ResourceConflictEntry:
    task_id: str
    task_name: str
    allocation_percent: float


@dataclass
class ResourceConflict:
    resource_id: str
    resource_name: str
    conflict_date: date
    total_allocation_percent: float
    entries: list[ResourceConflictEntry]


@dataclass
class ResourceLevelingAction:
    task_id: str
    task_name: str
    resource_id: str | None
    resource_name: str | None
    conflict_date: date | None
    shift_working_days: int
    old_start: date | None
    old_end: date | None
    new_start: date | None
    new_end: date | None
    reason: str


@dataclass
class ResourceLevelingResult:
    conflicts_before: int
    conflicts_after: int
    iterations: int
    actions: list[ResourceLevelingAction]


__all__ = [
    "ResourceConflictEntry",
    "ResourceConflict",
    "ResourceLevelingAction",
    "ResourceLevelingResult",
]
