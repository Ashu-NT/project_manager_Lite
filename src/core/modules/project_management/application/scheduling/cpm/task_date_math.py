"""Shared, calendar-parameterized per-task CPM date computation.

Before this module existed, SchedulingEngine and CPMCalculator each carried
their own byte-for-byte copy of "milestone vs duration" dependency
resolution, actual-date overriding, and (only on SchedulingEngine's side)
scheduling-constraint application. That let CPMCalculator's consumer (the
Portfolio heatmap) silently compute a different schedule than the live
SchedulingEngine path for the same project

Every consumer of per-task CPM date math (SchedulingEngine today; the
Portfolio heatmap's pure_cpm.run_cpm going forward) calls these same three
functions, parameterized only by which calendar to use. There is exactly one
implementation of "how a task's dates are computed" in the codebase.
"""

from __future__ import annotations

from datetime import date

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintType,
)
from src.core.modules.project_management.application.scheduling.cpm.dependency_schedule_math import (
    successor_boundary,
    successor_earliest_start_from_boundary,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency


def compute_milestone_dates(
    calendar: CalendarProtocol,
    task: Task,
    incoming_deps: list[TaskDependency],
    es: dict[str, date | None],
    ef: dict[str, date | None],
) -> tuple[date | None, date | None]:
    """Milestone / zero-duration task: earliest start == earliest finish."""
    if not incoming_deps:
        if task.start_date:
            return task.start_date, task.start_date
        return None, None

    candidates: list[date] = []
    for dep in incoming_deps:
        boundary = successor_boundary(
            calendar,
            dependency_type=dep.dependency_type,
            lag_days=dep.lag_days,
            predecessor_earliest_start=es.get(dep.predecessor_task_id),
            predecessor_earliest_finish=ef.get(dep.predecessor_task_id),
        )
        if boundary is not None:
            candidates.append(boundary.date)

    if not candidates:
        if task.start_date:
            return task.start_date, task.start_date
        return None, None

    est = max(candidates)
    return est, est


def compute_duration_dates(
    calendar: CalendarProtocol,
    task: Task,
    incoming_deps: list[TaskDependency],
    es: dict[str, date | None],
    ef: dict[str, date | None],
    duration: int,
) -> tuple[date | None, date | None]:
    """Task with duration > 0."""
    if not incoming_deps:
        if task.start_date:
            est = task.start_date
            eft = calendar.add_working_days(est, duration)
            return est, eft
        return None, None

    candidate_es: list[date] = []
    for dep in incoming_deps:
        boundary = successor_boundary(
            calendar,
            dependency_type=dep.dependency_type,
            lag_days=dep.lag_days,
            predecessor_earliest_start=es.get(dep.predecessor_task_id),
            predecessor_earliest_finish=ef.get(dep.predecessor_task_id),
        )
        if boundary is not None:
            candidate_es.append(
                successor_earliest_start_from_boundary(calendar, boundary, successor_duration_days=duration)
            )

    if not candidate_es:
        if task.start_date:
            est = task.start_date
            eft = calendar.add_working_days(est, duration)
            return est, eft
        return None, None

    est = max(candidate_es)
    eft = calendar.add_working_days(est, duration)
    return est, eft


def apply_actual_date_constraints(
    calendar: CalendarProtocol,
    task: Task,
    est: date | None,
    eft: date | None,
    duration_days: int,
) -> tuple[date | None, date | None]:
    """Enforce actual_start/actual_end onto computed ES/EF.

    - actual_end set => EF is fixed to actual_end; ES becomes actual_start if
      present, else EF - duration.
    - actual_start set (no actual_end) => ES cannot be earlier than
      actual_start; EF shifts accordingly if duration > 0.
    """
    a_start = getattr(task, "actual_start", None)
    a_end = getattr(task, "actual_end", None)

    if a_end is not None:
        fixed_ef = a_end
        if a_start is not None:
            fixed_es = a_start
        elif duration_days > 0:
            fixed_es = calendar.add_working_days(fixed_ef, -(duration_days - 1))
        else:
            fixed_es = fixed_ef
        return fixed_es, fixed_ef

    if a_start is not None:
        if est is None or a_start > est:
            est = a_start
            eft = est if duration_days <= 0 else calendar.add_working_days(est, duration_days)

    return est, eft


def apply_scheduling_constraints(
    calendar: CalendarProtocol,
    task: Task,
    est: date | None,
    eft: date | None,
) -> tuple[date | None, date | None]:
    """Apply forward-pass hard scheduling constraints (MSO, MFO, SNET, FNET).

    SNLT, FNLT, DEADLINE are validation-only -- reported by
    ConstraintValidator but never drive the forward-pass schedule. Skipped
    entirely once task.actual_end is set (the task is done).
    """
    if getattr(task, "actual_end", None) is not None:
        return est, eft

    raw_ct = getattr(task, "constraint_type", None)
    cd: date | None = getattr(task, "constraint_date", None)
    if raw_ct is None or cd is None:
        return est, eft

    try:
        ct = ConstraintType(str(raw_ct)) if not isinstance(raw_ct, ConstraintType) else raw_ct
    except ValueError:
        return est, eft

    duration = int(task.duration_days or 0)

    if ct == ConstraintType.MUST_START_ON:
        est = cd
        eft = calendar.add_working_days(cd, duration) if duration > 0 else cd

    elif ct == ConstraintType.MUST_FINISH_ON:
        eft = cd
        est = calendar.add_working_days(cd, -(duration - 1)) if duration > 0 else cd

    elif ct == ConstraintType.START_NO_EARLIER_THAN:
        if est is None or est < cd:
            est = cd
            eft = calendar.add_working_days(cd, duration) if duration > 0 else cd

    elif ct == ConstraintType.FINISH_NO_EARLIER_THAN:
        if eft is None or eft < cd:
            eft = cd
            est = calendar.add_working_days(cd, -(duration - 1)) if duration > 0 else cd

    return est, eft


__all__ = [
    "compute_milestone_dates",
    "compute_duration_dates",
    "apply_actual_date_constraints",
    "apply_scheduling_constraints",
]
