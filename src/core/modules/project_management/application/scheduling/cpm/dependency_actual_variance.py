"""Actual-vs-planned dependency variance facts.

Actual dates are historical truth and are never moved to satisfy a planned dependency
(``apply_actual_date_constraints`` always overrides the dependency-derived date, never the
reverse). This module reports, as a non-blocking fact, when a task's own recorded actual date
fell outside what its dependency graph required -- it never changes any date.

Reads ``CPMTaskInfo.dependency_implied_start/finish``, captured before the task's own
actual-date override was applied, so the comparison is against the graph's requirement rather
than circular.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.domain.tasks.task import Task


@dataclass(frozen=True, slots=True)
class DependencyActualVariance:
    """A task's own recorded actual date fell outside what its incoming
    dependencies required, given its predecessor's own best-known date.
    Non-blocking: a reported fact, not a raised error."""

    task_id: str
    task_name: str
    direction: str  # "start" or "finish"
    actual_date: date
    dependency_required_date: date
    difference_working_days: int
    code: str = "DEPENDENCY_ACTUAL_VARIANCE"


def find_dependency_actual_variances(
    tasks_by_id: dict[str, Task],
    cpm_result: dict[str, CPMTaskInfo],
    calendar,
) -> list[DependencyActualVariance]:
    variances: list[DependencyActualVariance] = []
    for task_id, task in tasks_by_id.items():
        info = cpm_result.get(task_id)
        if info is None:
            continue

        actual_start = getattr(task, "actual_start", None)
        if actual_start is not None and info.dependency_implied_start is not None:
            if actual_start < info.dependency_implied_start:
                variances.append(
                    _variance(
                        calendar,
                        task,
                        direction="start",
                        actual_date=actual_start,
                        required_date=info.dependency_implied_start,
                    )
                )

        actual_finish = getattr(task, "actual_end", None)
        if actual_finish is not None and info.dependency_implied_finish is not None:
            if actual_finish < info.dependency_implied_finish:
                variances.append(
                    _variance(
                        calendar,
                        task,
                        direction="finish",
                        actual_date=actual_finish,
                        required_date=info.dependency_implied_finish,
                    )
                )

    return variances


def _variance(
    calendar,
    task: Task,
    *,
    direction: str,
    actual_date: date,
    required_date: date,
) -> DependencyActualVariance:
    diff = calendar.working_days_between(actual_date, required_date) - 1
    return DependencyActualVariance(
        task_id=task.id,
        task_name=task.name,
        direction=direction,
        actual_date=actual_date,
        dependency_required_date=required_date,
        difference_working_days=diff,
    )


__all__ = ["DependencyActualVariance", "find_dependency_actual_variances"]
