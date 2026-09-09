"""Shared, calendar-parameterized per-task CPM date computation.

Every consumer of per-task CPM date math (`SchedulingEngine`, the Portfolio heatmap's
`pure_cpm.run_cpm`) calls these same functions, parameterized only by which calendar to use --
there is exactly one implementation of "how a task's dates are computed" in the codebase.
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
    shift_working_days,
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


def _coerce_task_constraint(task: Task) -> tuple[ConstraintType | None, date | None]:
    """Single shared parse of a task's (constraint_type, constraint_date)
    pair -- used by both the forward and backward constraint application
    so the two directions read the exact same interpretation of a task's
    constraint and cannot silently drift apart."""
    raw_ct = getattr(task, "constraint_type", None)
    cd: date | None = getattr(task, "constraint_date", None)
    if raw_ct is None or cd is None:
        return None, None
    try:
        ct = ConstraintType(str(raw_ct)) if not isinstance(raw_ct, ConstraintType) else raw_ct
    except ValueError:
        return None, None
    return ct, cd


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

    ct, cd = _coerce_task_constraint(task)
    if ct is None or cd is None:
        return est, eft

    duration = int(task.duration_days or 0)
    start_is_locked = getattr(task, "actual_start", None) is not None

    if ct == ConstraintType.MUST_START_ON:
        if start_is_locked:
            return est, eft
        est = cd
        eft = calendar.add_working_days(cd, duration) if duration > 0 else cd

    elif ct == ConstraintType.MUST_FINISH_ON:
        eft = cd
        if not start_is_locked:
            est = calendar.add_working_days(cd, -(duration - 1)) if duration > 0 else cd

    elif ct == ConstraintType.START_NO_EARLIER_THAN:
        if start_is_locked:
            return est, eft
        if est is None or est < cd:
            est = cd
            eft = calendar.add_working_days(cd, duration) if duration > 0 else cd

    elif ct == ConstraintType.FINISH_NO_EARLIER_THAN:
        if eft is None or eft < cd:
            eft = cd
            if not start_is_locked:
                est = calendar.add_working_days(cd, -(duration - 1)) if duration > 0 else cd

    return est, eft


def apply_resource_leveling_floor(
    calendar: CalendarProtocol,
    task: Task,
    est: date | None,
    eft: date | None,
) -> tuple[date | None, date | None]:
    """Unconditional forward-pass floor for an accepted resource-leveling placement
    (``Task.resource_leveling_not_before``) -- composes with (never replaces) whatever the
    dependency graph and ``apply_scheduling_constraints`` already produced, exactly like
    ``START_NO_EARLIER_THAN``'s own floor. This is what makes a resource-driven placement
    survive every subsequent ``run_cpm`` call, even for a task with an incoming dependency.

    Called AFTER ``apply_scheduling_constraints`` so a real, user-entered exact pin
    (MUST_START_ON/MUST_FINISH_ON) is never second-guessed by a resource placement -- this
    function only guards the composition; movability policy (`movability_policy.py`) is
    responsible for never proposing a move for a pinned task in the first place.

    Skipped once ``actual_start``/``actual_end`` locks the task -- historical fact always wins
    over a scheduler-generated placement, same precedence every other constraint respects.
    """
    floor = getattr(task, "resource_leveling_not_before", None)
    if floor is None:
        return est, eft
    if getattr(task, "actual_start", None) is not None or getattr(task, "actual_end", None) is not None:
        return est, eft
    if est is not None and est >= floor:
        return est, eft
    duration = int(task.duration_days or 0)
    new_est = floor
    new_eft = calendar.add_working_days(new_est, duration) if duration > 0 else new_est
    return new_est, new_eft


def apply_backward_scheduling_constraints(
    calendar: CalendarProtocol,
    task: Task,
    est: date | None,
    eft: date | None,
    raw_lst: date | None,
    raw_lft: date | None,
) -> tuple[date | None, date | None]:
    """Adjust one task's network-derived (raw_lst, raw_lft) backward-pass late dates for its
    own actual-date lock and/or scheduling constraint, so latest start/finish -- and therefore
    total float and criticality -- reflect what the task can actually do, not just what the
    dependency graph alone would allow.

    Mirrors ``apply_scheduling_constraints``'s forward-pass semantics, reusing the task's own
    already-computed ``est``/``eft`` (never re-deriving a constraint date independently) so the
    two directions cannot drift apart -- see ``_coerce_task_constraint``.

    START_NO_EARLIER_THAN / FINISH_NO_EARLIER_THAN need no adjustment here: the floor they apply
    already raised ``est``/``eft`` forward, so this task's own ``raw_lst``/``raw_lft`` -- bounded
    by its own successors, not its own floor -- is already correct.

    An actual-date lock takes precedence over any constraint: a completed task (`actual_end`) has
    ls/lf pinned to est/eft; a started-but-unfinished task (`actual_start` only) pins ls to est but
    leaves lf to the network/ceiling logic, since the not-yet-happened portion can still have
    finish-side slack. MUST_START_ON/MUST_FINISH_ON are exact pins (zero float on the pinned side).
    START_NO_LATER_THAN/FINISH_NO_LATER_THAN are ceilings that cap ls/lf at the constraint date --
    an infeasible ceiling is not clamped away and can legitimately produce negative float (see
    `results.py`). `task.deadline` gets the same ceiling treatment as FINISH_NO_LATER_THAN but
    stays a separate field, never becoming a scheduling constraint in its own right.
    """
    if est is None or eft is None:
        return raw_lst, raw_lft

    actual_start = getattr(task, "actual_start", None)
    actual_end = getattr(task, "actual_end", None)
    if actual_end is not None:
        return est, eft

    ct, cd = _coerce_task_constraint(task)
    duration = int(task.duration_days or 0)

    if ct == ConstraintType.MUST_START_ON and actual_start is None:
        return est, eft

    if ct == ConstraintType.MUST_FINISH_ON:
        return est, eft

    lst = est if actual_start is not None else raw_lst
    lft = raw_lft

    if ct == ConstraintType.START_NO_LATER_THAN and actual_start is None:
        if lst is not None and cd is not None and lst > cd:
            lst = cd
            lft = shift_working_days(calendar, lst, duration - 1) if duration > 0 else lst

    if ct == ConstraintType.FINISH_NO_LATER_THAN:
        if lft is not None and cd is not None and lft > cd:
            lft = cd
            if actual_start is None:
                lst = shift_working_days(calendar, lft, -(duration - 1)) if duration > 0 else lft

    deadline = getattr(task, "deadline", None)
    if deadline is not None and lft is not None and lft > deadline:
        lft = deadline
        if actual_start is None:
            lst = shift_working_days(calendar, lft, -(duration - 1)) if duration > 0 else lft

    return lst, lft


__all__ = [
    "compute_milestone_dates",
    "compute_duration_dates",
    "apply_actual_date_constraints",
    "apply_scheduling_constraints",
    "apply_resource_leveling_floor",
    "apply_backward_scheduling_constraints",
]
