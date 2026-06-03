from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.date_compute import (
    compute_task_dates_common,
)
from src.core.modules.project_management.application.scheduling.cpm.graph import (
    build_project_dependency_graph,
)
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.application.scheduling.cpm.passes import (
    run_backward_pass,
    run_forward_pass,
)
from src.core.modules.project_management.application.scheduling.cpm.results import (
    build_schedule_result,
)
from src.core.modules.project_management.domain.enums import DependencyType


@dataclass
class CPMResult:
    """Output of a full CPM calculation pass."""
    schedule: Dict[str, CPMTaskInfo]
    project_early_finish: Optional[date]
    critical_path_task_ids: List[str]


class CPMCalculator:
    """
    Pure CPM calculation service — no persistence, no side effects.

    SchedulingEngine delegates CPM maths here.  Callers receive a CPMResult
    without any DB write.  Application services decide whether to persist.
    """

    def __init__(self, calendar: CalendarProtocol) -> None:
        self._calendar = calendar

    def calculate(
        self,
        tasks_by_id: Dict[str, Task],
        deps: List[TaskDependency],
    ) -> CPMResult:
        """
        Run forward + backward pass on the supplied task/dependency graph.

        Tasks are NOT mutated; start_date/end_date writes stay with the caller.
        """
        if not tasks_by_id:
            return CPMResult(schedule={}, project_early_finish=None, critical_path_task_ids=[])

        topo_order, deps_by_successor, deps_by_predecessor = build_project_dependency_graph(
            tasks_by_id=tasks_by_id,
            deps=deps,
            priority_value=self._priority_value,
        )

        es, ef, project_early_finish = run_forward_pass(
            tasks_by_id=tasks_by_id,
            topo_order=topo_order,
            deps_by_successor=deps_by_successor,
            compute_task_dates=self._compute_task_dates,
        )
        ls, lf = run_backward_pass(
            tasks_by_id=tasks_by_id,
            topo_order=topo_order,
            deps_by_predecessor=deps_by_predecessor,
            es=es,
            ef=ef,
            project_early_finish=project_early_finish,
            calendar=self._calendar,
        )

        schedule = build_schedule_result(
            tasks_by_id={tid: _task_snapshot(t) for tid, t in tasks_by_id.items()},
            es=es,
            ef=ef,
            ls=ls,
            lf=lf,
            calendar=self._calendar,
        )

        critical_ids = [tid for tid, info in schedule.items() if info.is_critical]
        return CPMResult(
            schedule=schedule,
            project_early_finish=project_early_finish,
            critical_path_task_ids=critical_ids,
        )

    # ── internal helpers ────────────────────────────────────────────────────

    def _compute_task_dates(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
    ) -> tuple[Optional[date], Optional[date]]:
        return compute_task_dates_common(
            task=task,
            incoming_deps=incoming_deps,
            es=es,
            ef=ef,
            compute_milestone=self._compute_dates_milestone,
            compute_with_duration=self._compute_dates_with_duration,
            apply_actual_constraints=self._apply_actual_constraints,
        )

    def _compute_dates_milestone(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
    ) -> tuple[Optional[date], Optional[date]]:
        if not incoming_deps:
            if task.start_date:
                return task.start_date, task.start_date
            return None, None
        candidates: List[date] = []
        for dep in incoming_deps:
            pred_es = es.get(dep.predecessor_task_id)
            pred_ef = ef.get(dep.predecessor_task_id)
            if pred_es is None and pred_ef is None:
                continue
            if dep.dependency_type == DependencyType.FINISH_TO_START:
                if pred_ef:
                    candidates.append(self._calendar.add_working_days(pred_ef, dep.lag_days + 2))
            elif dep.dependency_type == DependencyType.START_TO_START:
                if pred_es:
                    candidates.append(self._calendar.add_working_days(pred_es, dep.lag_days))
            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                if pred_ef:
                    candidates.append(self._calendar.add_working_days(pred_ef, dep.lag_days))
            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                if pred_es:
                    candidates.append(self._calendar.add_working_days(pred_es, dep.lag_days))
        if not candidates:
            if task.start_date:
                return task.start_date, task.start_date
            return None, None
        est = max(candidates)
        return est, est

    def _compute_dates_with_duration(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
        duration: int,
    ) -> tuple[Optional[date], Optional[date]]:
        if not incoming_deps:
            if task.start_date:
                est = task.start_date
                eft = self._calendar.add_working_days(est, duration)
                return est, eft
            return None, None
        candidate_es: List[date] = []
        for dep in incoming_deps:
            pred_es = es.get(dep.predecessor_task_id)
            pred_ef = ef.get(dep.predecessor_task_id)
            if pred_es is None and pred_ef is None:
                continue
            if dep.dependency_type == DependencyType.FINISH_TO_START:
                if pred_ef:
                    candidate_es.append(self._calendar.add_working_days(pred_ef, dep.lag_days + 2))
            elif dep.dependency_type == DependencyType.START_TO_START:
                if pred_es:
                    candidate_es.append(self._calendar.add_working_days(pred_es, dep.lag_days))
            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                if pred_ef:
                    ef_s = self._calendar.add_working_days(pred_ef, dep.lag_days)
                    cand_es = self._calendar.add_working_days(ef_s, -(duration - 1)) if duration > 0 else ef_s
                    candidate_es.append(cand_es)
            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                if pred_es:
                    ef_s = self._calendar.add_working_days(pred_es, dep.lag_days)
                    cand_es = self._calendar.add_working_days(ef_s, -(duration - 1)) if duration > 0 else ef_s
                    candidate_es.append(cand_es)
        if not candidate_es:
            if task.start_date:
                est = task.start_date
                eft = self._calendar.add_working_days(est, duration)
                return est, eft
            return None, None
        est = max(candidate_es)
        eft = self._calendar.add_working_days(est, duration)
        return est, eft

    def _apply_actual_constraints(
        self,
        task: Task,
        est: Optional[date],
        eft: Optional[date],
        duration_days: int,
    ) -> tuple[Optional[date], Optional[date]]:
        a_start = getattr(task, "actual_start", None)
        a_end = getattr(task, "actual_end", None)
        if a_end is not None:
            fixed_ef = a_end
            if a_start is not None:
                fixed_es = a_start
            elif duration_days > 0:
                fixed_es = self._calendar.add_working_days(fixed_ef, -(duration_days - 1))
            else:
                fixed_es = fixed_ef
            return fixed_es, fixed_ef
        if a_start is not None:
            if est is None or a_start > est:
                est = a_start
                eft = est if duration_days <= 0 else self._calendar.add_working_days(est, duration_days)
        return est, eft

    def _priority_value(self, task: Task) -> int:
        priority = getattr(task, "priority", None)
        if priority is None:
            return 50
        if hasattr(priority, "value"):
            priority = priority.value
        if isinstance(priority, (int, float)):
            return int(priority)
        if isinstance(priority, str):
            norm = priority.strip().upper()
            if norm in ("HIGH", "H"):
                return 10
            if norm in ("MEDIUM", "M", "NORMAL"):
                return 50
            if norm in ("LOW", "L"):
                return 90
        return 50


def _task_snapshot(task: Task) -> Task:
    """Return a shallow copy of task so CPMCalculator never mutates the caller's objects."""
    from dataclasses import replace
    return replace(task)


__all__ = ["CPMCalculator", "CPMResult"]
