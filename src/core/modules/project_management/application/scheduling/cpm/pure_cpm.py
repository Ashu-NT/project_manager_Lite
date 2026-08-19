"""Pure, stateless CPM entry point for consumers that need a computed
schedule without a live SchedulingEngine (session, task repo, etc).

This is the single non-persisting CPM implementation in the codebase.
Before this module existed, ``CPMCalculator`` filled this role with its own
duplicated dependency-date math and, critically, applied no scheduling
constraints at all -- while ``SchedulingEngine`` (the live, persisting path)
did. That meant the same project could report a different schedule on the
Portfolio heatmap than on the Dashboard/Task Detail, purely because of which
screen was open. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§11/§12/Phase D.

``run_cpm`` shares the exact same primitives SchedulingEngine uses
(``build_project_dependency_graph``, ``run_forward_pass``,
``run_backward_pass``, ``build_schedule_result``, and the
``task_date_math``/``dependency_schedule_math`` functions) -- it differs
from SchedulingEngine only in that it takes an already-fetched task/
dependency set and a single calendar, and never touches the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.modules.project_management.application.scheduling.cpm.date_compute import (
    compute_task_dates_common,
)
from src.core.modules.project_management.application.scheduling.cpm.graph import (
    build_project_dependency_graph,
)
from src.core.modules.project_management.application.scheduling.cpm.passes import (
    run_backward_pass,
    run_forward_pass,
)
from src.core.modules.project_management.application.scheduling.cpm.results import (
    build_schedule_result,
)
from src.core.modules.project_management.application.scheduling.cpm.task_date_math import (
    apply_actual_date_constraints,
    apply_scheduling_constraints,
    compute_duration_dates,
    compute_milestone_dates,
)
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.application.scheduling.utils.task_priority import (
    get_task_priority_value,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency


@dataclass
class CPMResult:
    """Output of a full pure CPM calculation pass."""

    schedule: dict[str, CPMTaskInfo]
    project_early_finish: date | None
    critical_path_task_ids: list[str]


def run_cpm(
    calendar: CalendarProtocol,
    tasks_by_id: dict[str, Task],
    deps: list[TaskDependency],
    *,
    apply_constraints: bool = True,
) -> CPMResult:
    """Forward + backward CPM pass over an already-fetched task/dependency
    set. No persistence, no side effects.

    ``apply_constraints`` defaults to True so this matches SchedulingEngine's
    behavior by default; pass False only for callers that deliberately want
    a constraint-blind schedule (none exist today -- the whole point of
    consolidating onto this function is that no consumer should need to).
    """
    if not tasks_by_id:
        return CPMResult(schedule={}, project_early_finish=None, critical_path_task_ids=[])

    dependency_implied_dates: dict[str, tuple[date | None, date | None]] = {}

    def _compute_task_dates(task, incoming_deps, es, ef):
        def _capture(dep_est, dep_eft):
            if incoming_deps:
                dependency_implied_dates[task.id] = (dep_est, dep_eft)

        est, eft = compute_task_dates_common(
            task=task,
            incoming_deps=incoming_deps,
            es=es,
            ef=ef,
            compute_milestone=lambda t, d, e, f: compute_milestone_dates(calendar, t, d, e, f),
            compute_with_duration=lambda t, d, e, f, dur: compute_duration_dates(calendar, t, d, e, f, dur),
            apply_actual_constraints=lambda t, e, f, dur: apply_actual_date_constraints(calendar, t, e, f, dur),
            on_dependency_implied=_capture,
        )
        if apply_constraints:
            est, eft = apply_scheduling_constraints(calendar, task, est, eft)
        return est, eft

    topo_order, deps_by_successor, deps_by_predecessor = build_project_dependency_graph(
        tasks_by_id=tasks_by_id,
        deps=deps,
        priority_value=get_task_priority_value,
    )

    es, ef, project_early_finish = run_forward_pass(
        tasks_by_id=tasks_by_id,
        topo_order=topo_order,
        deps_by_successor=deps_by_successor,
        compute_task_dates=_compute_task_dates,
    )
    ls, lf = run_backward_pass(
        tasks_by_id=tasks_by_id,
        topo_order=topo_order,
        deps_by_predecessor=deps_by_predecessor,
        es=es,
        ef=ef,
        project_early_finish=project_early_finish,
        calendar=calendar,
    )

    schedule = build_schedule_result(
        tasks_by_id=dict(tasks_by_id),
        es=es,
        ef=ef,
        ls=ls,
        lf=lf,
        calendar=calendar,
        dependency_implied=dependency_implied_dates,
    )
    critical_ids = [tid for tid, info in schedule.items() if info.is_critical]
    return CPMResult(
        schedule=schedule,
        project_early_finish=project_early_finish,
        critical_path_task_ids=critical_ids,
    )


__all__ = ["run_cpm", "CPMResult"]
