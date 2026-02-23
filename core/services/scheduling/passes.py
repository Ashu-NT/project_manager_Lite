from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional

from core.exceptions import ValidationError
from core.models import DependencyType, Task, TaskDependency
from core.services.work_calendar.engine import WorkCalendarEngine


ForwardComputeFn = Callable[
    [Task, List[TaskDependency], Dict[str, Optional[date]], Dict[str, Optional[date]]],
    tuple[Optional[date], Optional[date]],
]


def run_forward_pass(
    tasks_by_id: Dict[str, Task],
    topo_order: List[str],
    deps_by_successor: Dict[str, List[TaskDependency]],
    compute_task_dates: ForwardComputeFn,
) -> tuple[Dict[str, Optional[date]], Dict[str, Optional[date]], date]:
    es: Dict[str, Optional[date]] = {task_id: None for task_id in tasks_by_id}
    ef: Dict[str, Optional[date]] = {task_id: None for task_id in tasks_by_id}

    for task_id in topo_order:
        task = tasks_by_id[task_id]
        incoming = deps_by_successor.get(task_id, [])
        est, eft = compute_task_dates(task, incoming, es, ef)
        es[task_id] = est
        ef[task_id] = eft

    project_ef_dates = [d for d in ef.values() if d is not None]
    if not project_ef_dates:
        raise ValidationError("No computed finish dates; ensure tasks have durations or start dates.")
    return es, ef, max(project_ef_dates)


def run_backward_pass(
    tasks_by_id: Dict[str, Task],
    topo_order: List[str],
    deps_by_predecessor: Dict[str, List[TaskDependency]],
    es: Dict[str, Optional[date]],
    ef: Dict[str, Optional[date]],
    project_early_finish: date,
    calendar: WorkCalendarEngine,
) -> tuple[Dict[str, Optional[date]], Dict[str, Optional[date]]]:
    ls: Dict[str, Optional[date]] = {task_id: None for task_id in tasks_by_id}
    lf: Dict[str, Optional[date]] = {task_id: None for task_id in tasks_by_id}

    end_tasks = [task_id for task_id in tasks_by_id if task_id not in deps_by_predecessor]
    for task_id in end_tasks:
        duration = tasks_by_id[task_id].duration_days or 0
        lf[task_id] = project_early_finish
        if duration <= 0:
            ls[task_id] = project_early_finish
        else:
            ls[task_id] = calendar.add_working_days(project_early_finish, -(duration - 1))

    for task_id in reversed(topo_order):
        outgoing = deps_by_predecessor.get(task_id, [])
        if not outgoing:
            if ls[task_id] is None and es[task_id] is not None:
                ls[task_id] = es[task_id]
                lf[task_id] = ef[task_id]
            continue

        cand_ls_dates: List[date] = []
        cand_lf_dates: List[date] = []
        duration = tasks_by_id[task_id].duration_days or 0

        for dep in outgoing:
            succ_id = dep.successor_task_id
            succ_ls = ls[succ_id]
            succ_lf = lf[succ_id]
            if succ_ls is None and succ_lf is None:
                continue

            if dep.dependency_type == DependencyType.FINISH_TO_START:
                if succ_ls is not None:
                    cand_lf_dates.append(calendar.add_working_days(succ_ls, -dep.lag_days))
            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                if succ_lf is not None:
                    cand_lf_dates.append(calendar.add_working_days(succ_lf, -dep.lag_days))
            elif dep.dependency_type == DependencyType.START_TO_START:
                if succ_ls is not None:
                    cand_ls_dates.append(calendar.add_working_days(succ_ls, -dep.lag_days))
            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                if succ_lf is not None:
                    cand_ls_dates.append(calendar.add_working_days(succ_lf, -dep.lag_days))

        if cand_lf_dates:
            lf_candidate = min(cand_lf_dates)
            lf[task_id] = lf_candidate
            if duration > 0:
                ls[task_id] = calendar.add_working_days(lf_candidate, -(duration - 1))
            else:
                ls[task_id] = lf_candidate
        elif cand_ls_dates:
            ls_candidate = min(cand_ls_dates)
            ls[task_id] = ls_candidate
            if duration > 0:
                lf[task_id] = calendar.add_working_days(ls_candidate, duration - 1)
            else:
                lf[task_id] = ls_candidate
        elif es[task_id] is not None:
            ls[task_id] = es[task_id]
            lf[task_id] = ef[task_id]

    return ls, lf

