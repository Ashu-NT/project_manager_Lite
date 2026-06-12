"""Shared task priority helper used by scheduling and leveling."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.modules.project_management.domain.tasks.task import Task


def get_task_priority_value(task: "Task") -> int:
    """
    Return a sort key where lower = higher scheduling priority.

    Supports enum with .value, int, or 'HIGH'/'MEDIUM'/'LOW' strings.
    Unknown/missing defaults to medium (50).
    """
    priority = getattr(task, "priority", None)
    if priority is None:
        return 50
    if hasattr(priority, "value"):
        priority = priority.value
    if isinstance(priority, (int, float)):
        return int(priority)
    if isinstance(priority, str):
        norm = priority.strip().upper()
        if norm in ("HIGH", "H"):
            return 10
        if norm in ("MEDIUM", "M", "NORMAL"):
            return 50
        if norm in ("LOW", "L"):
            return 90
    return 50


__all__ = ["get_task_priority_value"]
