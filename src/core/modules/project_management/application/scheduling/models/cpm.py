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
    # The task's earliest start/finish as required by its incoming
    # TaskDependency edges alone, captured BEFORE any of the task's own
    # hard scheduling constraints (Must Start On / Must Finish On) were
    # applied. None when the task has no incoming dependencies. Lets
    # ConstraintValidator report when a hard constraint silently overrode
    # what the dependency graph required, instead of the override being
    # invisible -- see
    # docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
    # Phase F.
    dependency_implied_start: date | None = None
    dependency_implied_finish: date | None = None


__all__ = ["CPMTaskInfo"]
