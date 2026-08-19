from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency


def compute_task_dates_common(
    task: Task,
    incoming_deps: list[TaskDependency],
    es: dict[str, date | None],
    ef: dict[str, date | None],
    compute_milestone,
    compute_with_duration,
    apply_actual_constraints,
    *,
    on_dependency_implied=None,
) -> tuple[date | None, date | None]:
    duration = int(task.duration_days or 0)
    if duration <= 0:
        est, eft = compute_milestone(task, incoming_deps, es, ef)
    else:
        est, eft = compute_with_duration(task, incoming_deps, es, ef, duration)
    if on_dependency_implied is not None:
        # Pure dependency-graph result, BEFORE actuals override it. Needed
        # by both the constraint-conflict fact (Phase F) and the
        # actual-vs-planned variance fact (Phase J) -- neither can be
        # computed correctly from the post-actual value, since a task with
        # its own actual_start already folded into est/eft is not a useful
        # basis for asking "did this task's actual execution violate what
        # its dependency graph required."
        on_dependency_implied(est, eft)
    return apply_actual_constraints(task, est, eft, duration)


__all__ = ["compute_task_dates_common"]
