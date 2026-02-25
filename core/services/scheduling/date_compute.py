from __future__ import annotations

from datetime import date
from typing import Optional

from core.models import Task, TaskDependency


def compute_task_dates_common(
    task: Task,
    incoming_deps: list[TaskDependency],
    es: dict[str, Optional[date]],
    ef: dict[str, Optional[date]],
    compute_milestone,
    compute_with_duration,
    apply_actual_constraints,
) -> tuple[Optional[date], Optional[date]]:
    duration = int(task.duration_days or 0)
    if duration <= 0:
        est, eft = compute_milestone(task, incoming_deps, es, ef)
    else:
        est, eft = compute_with_duration(task, incoming_deps, es, ef, duration)
    return apply_actual_constraints(task, est, eft, duration)


__all__ = ["compute_task_dates_common"]
