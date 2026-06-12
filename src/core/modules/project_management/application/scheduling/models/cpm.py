"""Shared CPM result DTO."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.tasks.task import Task


@dataclass
class CPMTaskInfo:
    task: Task
    earliest_start: date | None
    earliest_finish: date | None
    latest_start: date | None
    latest_finish: date | None
    total_float_days: int | None
    is_critical: bool
    deadline: date | None = None
    late_by_days: int | None = None


__all__ = ["CPMTaskInfo"]
