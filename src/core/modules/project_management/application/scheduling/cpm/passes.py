from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

from datetime import date
from typing import Callable

from src.core.platform.common.exceptions import ValidationError
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.dependency_schedule_math import (
    predecessor_late_boundary,
    shift_working_days,
)
from src.core.modules.project_management.application.scheduling.cpm.task_date_math import (
    apply_backward_scheduling_constraints,
)


ForwardComputeFn = Callable[
    [Task, list[TaskDependency], dict[str, date | None], dict[str, date | None]],
    tuple[date | None, date | None],
]


def run_forward_pass(
    tasks_by_id: dict[str, Task],
    topo_order: list[str],
    deps_by_successor: dict[str, list[TaskDependency]],
    compute_task_dates: ForwardComputeFn,
) -> tuple[dict[str, date | None], dict[str, date | None], date]:
    es: dict[str, date | None] = {task_id: None for task_id in tasks_by_id}
    ef: dict[str, date | None] = {task_id: None for task_id in tasks_by_id}

    for task_id in topo_order:
        task = tasks_by_id[task_id]
        incoming = deps_by_successor.get(task_id, [])
        est, eft = compute_task_dates(task, incoming, es, ef)
        es[task_id] = est
        ef[task_id] = eft

    project_ef_dates = [d for d in ef.values() if d is not None]
    if not project_ef_dates:
        # All tasks returned None — root tasks likely have no start_date.
        # Anchor unanchored root tasks to the earliest known date in the project
        # (or today), then re-run the FULL forward pass so successors propagate
        # correctly from the newly anchored roots.
        known_starts = [
            t.start_date
            for t in tasks_by_id.values()
            if getattr(t, "start_date", None) is not None
        ]
        default_start: date = min(known_starts) if known_starts else date.today()

        # Patch root tasks that have no start_date
        patched: dict[str, Task] = {}
        for task_id, task in tasks_by_id.items():
            incoming = deps_by_successor.get(task_id, [])
            if not incoming and not getattr(task, "start_date", None):
                patched[task_id] = _task_with_default_start(task, default_start)
            else:
                patched[task_id] = task

        # Re-run forward pass with patched tasks so successors pick up the dates
        es = {task_id: None for task_id in tasks_by_id}
        ef = {task_id: None for task_id in tasks_by_id}
        for task_id in topo_order:
            task = patched[task_id]
            incoming = deps_by_successor.get(task_id, [])
            est, eft = compute_task_dates(task, incoming, es, ef)
            es[task_id] = est
            ef[task_id] = eft

        project_ef_dates = [d for d in ef.values() if d is not None]
        if not project_ef_dates:
            raise ValidationError(
                "No computed finish dates. Ensure at least one task has a start date "
                "or is linked via a dependency to an anchored task."
            )

    return es, ef, max(project_ef_dates)


def _task_with_default_start(task: Task, default_start: date) -> Task:
    """Return a copy of task with default_start as its start_date."""
    from dataclasses import replace
    return replace(task, start_date=default_start)


def run_backward_pass(
    tasks_by_id: dict[str, Task],
    topo_order: list[str],
    deps_by_predecessor: dict[str, list[TaskDependency]],
    es: dict[str, date | None],
    ef: dict[str, date | None],
    project_early_finish: date,
    calendar: CalendarProtocol,
) -> tuple[dict[str, date | None], dict[str, date | None]]:
    ls: dict[str, date | None] = {task_id: None for task_id in tasks_by_id}
    lf: dict[str, date | None] = {task_id: None for task_id in tasks_by_id}

    def _adjust(task_id: str, raw_ls: date | None, raw_lf: date | None) -> None:
        task = tasks_by_id[task_id]
        ls[task_id], lf[task_id] = apply_backward_scheduling_constraints(
            calendar, task, es[task_id], ef[task_id], raw_ls, raw_lf
        )

    end_tasks = [task_id for task_id in tasks_by_id if task_id not in deps_by_predecessor]
    for task_id in end_tasks:
        duration = tasks_by_id[task_id].duration_days or 0
        raw_lf = project_early_finish
        if duration <= 0:
            raw_ls = project_early_finish
        else:
            raw_ls = calendar.add_working_days(project_early_finish, -(duration - 1))
        _adjust(task_id, raw_ls, raw_lf)

    for task_id in reversed(topo_order):
        outgoing = deps_by_predecessor.get(task_id, [])
        if not outgoing:
            if ls[task_id] is None and es[task_id] is not None:
                _adjust(task_id, es[task_id], ef[task_id])
            continue

        duration = tasks_by_id[task_id].duration_days or 0

        # Every outgoing edge -- whatever its type -- is normalized into a
        # single LATEST-START bound before taking the minimum. This is the
        # fix for the old shadowing bug: previously, FS/FF-derived bounds
        # (grouped as "cand_lf_dates") were preferred outright over
        # SS/SF-derived bounds ("cand_ls_dates") whenever both existed on the
        # same predecessor, silently discarding the SS/SF constraints. See
        # docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md §11.
        candidate_ls_bounds: list[date] = []
        for dep in outgoing:
            succ_id = dep.successor_task_id
            late = predecessor_late_boundary(
                calendar,
                dependency_type=dep.dependency_type,
                lag_days=dep.lag_days,
                successor_latest_start=ls[succ_id],
                successor_latest_finish=lf[succ_id],
                predecessor_duration_days=duration,
            )
            if late is not None:
                candidate_ls_bounds.append(late.latest_start)

        if candidate_ls_bounds:
            ls_candidate = min(candidate_ls_bounds)
            raw_lf = (
                shift_working_days(calendar, ls_candidate, duration - 1)
                if duration > 0
                else ls_candidate
            )
            _adjust(task_id, ls_candidate, raw_lf)
        elif es[task_id] is not None:
            _adjust(task_id, es[task_id], ef[task_id])

    return ls, lf
