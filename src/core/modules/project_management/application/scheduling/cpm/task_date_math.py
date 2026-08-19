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
    constraint and cannot silently drift apart (R4.4 backward-CPM pass,
    §15)."""
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
    """R4.4: unconditional forward-pass floor for an ACCEPTED resource-
    leveling placement (``Task.resource_leveling_not_before``) -- composes
    with (never replaces) whatever the dependency graph and
    ``apply_scheduling_constraints`` already produced, exactly like
    ``START_NO_EARLIER_THAN``'s own floor. This is what makes a
    resource-driven placement survive every subsequent canonical
    ``run_cpm`` call even for a task with an incoming dependency -- the
    defect ``test_leveling_dependency_boundary.py`` pins (pre-R4.4,
    leveling wrote raw ``Task.start_date``, which the forward pass
    ignores outright whenever a usable incoming dependency exists).

    Called AFTER ``apply_scheduling_constraints`` so a real, user-entered
    exact pin (MUST_START_ON/MUST_FINISH_ON) is never second-guessed by a
    resource placement -- movability policy (leveling_policy.py) is
    responsible for never proposing a move for a pinned task in the
    first place; this function only guards the composition, it does not
    enforce that policy itself.

    Skipped once ``actual_start``/``actual_end`` locks the task --
    historical fact always wins over a scheduler-generated placement,
    same precedence every other constraint already respects.
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
    """Adjust one task's network-derived (raw_lst, raw_lft) backward-pass
    late dates for its own actual-date lock and/or scheduling constraint,
    so LATEST START/FINISH -- and therefore total float and criticality --
    reflect what the task can ACTUALLY do, not just what the dependency
    graph alone would allow (R4.4 constraint-aware backward CPM pass).

    Mirrors ``apply_scheduling_constraints``'s forward-pass semantics
    exactly, reusing the task's own already-computed ``est``/``eft``
    (never re-deriving a constraint date independently) so the two
    directions cannot drift apart -- see ``_coerce_task_constraint``.

    START_NO_EARLIER_THAN / FINISH_NO_EARLIER_THAN need NO adjustment
    here and are intentionally not handled below: the floor they apply
    already raised ``est``/``eft`` forward, which flows into every
    downstream successor computation already -- this task's own
    ``raw_lst``/``raw_lft`` is bounded by ITS OWN successors (or the
    project finish), not by its own floor, so it is already correct
    as-is once ``est``/``eft`` reflect the floor.

    - actual_end set (completed): ls/lf = est/eft, unconditionally. A
      historical fact; nothing else can move it.
    - actual_start set, no actual_end (started, unfinished): ls = est
      (the start already happened, so it cannot show fictitious movable
      float) -- lf is left to the network/ceiling logic below, since the
      remaining, not-yet-happened portion of the task can still
      legitimately have finish-side slack or a finish-side ceiling.
    - MUST_START_ON (and not already actual-locked): ls = est, and since
      forward derives eft from est+duration in the very same branch,
      lf = eft too -- an exact pin ties both dimensions to zero float
      together.
    - MUST_FINISH_ON: lf = eft (exact pin), active even once started,
      matching apply_scheduling_constraints's own "always applies unless
      actual_end is set" rule.
    - START_NO_LATER_THAN (ceiling, pre-start only): caps ls at the
      constraint date when the network-implied ls would be later,
      deriving lf from the now-capped ls. Can legitimately push ls below
      est, producing negative float -- an infeasible ceiling is not
      clamped away (see results.py).
    - FINISH_NO_LATER_THAN (ceiling): caps lf at the constraint date;
      re-derives ls from the capped lf, UNLESS the start already
      happened (actual_start set), in which case ls stays pinned to est
      and only lf is capped -- capping ls too would fabricate a change
      to a date that already occurred.
    - Deadline (task.deadline, independent of constraint_type): same
      ceiling treatment as FINISH_NO_LATER_THAN, applied on top of
      whatever constraint_type already produced -- Deadline stays a
      separate field/fact and never becomes a scheduling constraint in
      its own right.
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
