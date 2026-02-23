# core/services/scheduling_service.py
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from core.interfaces import DependencyRepository, TaskRepository
from core.models import DependencyType, Task, TaskDependency
from core.services.scheduling.graph import build_project_dependency_graph
from core.services.scheduling.models import CPMTaskInfo
from core.services.scheduling.passes import run_backward_pass, run_forward_pass
from core.services.scheduling.results import build_schedule_result
from core.services.work_calendar.engine import WorkCalendarEngine


class SchedulingEngine:
    """
    CPM-style scheduling engine:
    - Forward pass: ES/EF
    - Backward pass: LS/LF
    - FS, FF, SS, SF with lag_days
    - Uses WorkCalendarEngine for working-day arithmetic
    """

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        calendar: WorkCalendarEngine,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._calendar: WorkCalendarEngine = calendar

    def recalculate_project_schedule(self, project_id: str) -> Dict[str, CPMTaskInfo]:
        """
        Full CPM calculation for a project:
        - computes ES/EF (forward) and LS/LF (backward)
        - updates Task.start_date / Task.end_date from ES/EF
        - returns CPMTaskInfo per task
        """
        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return {}

        tasks_by_id: Dict[str, Task] = {t.id: t for t in tasks}
        deps: List[TaskDependency] = self._dependency_repo.list_by_project(project_id)

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

        result = build_schedule_result(
            tasks_by_id=tasks_by_id,
            es=es,
            ef=ef,
            ls=ls,
            lf=lf,
            calendar=self._calendar,
        )

        try:
            for info in result.values():
                self._task_repo.update(info.task)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        return result

    def _compute_task_dates(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
    ) -> tuple[Optional[date], Optional[date]]:
        duration = int(task.duration_days or 0)
        if duration <= 0:
            est, eft = self._compute_dates_milestone(task, incoming_deps, es, ef)
        else:
            est, eft = self._compute_dates_with_duration(task, incoming_deps, es, ef, duration)
        return self._apply_actual_constraints(task, est, eft, duration)

    def _compute_dates_milestone(
        self,
        task: Task,
        incoming_deps: List[TaskDependency],
        es: Dict[str, Optional[date]],
        ef: Dict[str, Optional[date]],
    ) -> tuple[Optional[date], Optional[date]]:
        """
        Milestone or 0-duration task: ES = EF.
        """
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
                    candidates.append(self._calendar.add_working_days(pred_ef, dep.lag_days))
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
        """
        Normal task with duration > 0.
        """
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
                    candidate_es.append(self._calendar.add_working_days(pred_ef, dep.lag_days))

            elif dep.dependency_type == DependencyType.START_TO_START:
                if pred_es:
                    candidate_es.append(self._calendar.add_working_days(pred_es, dep.lag_days))

            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                # EF_s >= EF_p + lag => ES_s >= EF_p + lag - duration_s + 1
                if pred_ef:
                    ef_s = self._calendar.add_working_days(pred_ef, dep.lag_days)
                    if duration > 0:
                        cand_es = self._calendar.add_working_days(ef_s, -(duration - 1))
                    else:
                        cand_es = ef_s
                    candidate_es.append(cand_es)

            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                # EF_s >= ES_p + lag => ES_s >= ES_p + lag - duration_s + 1
                if pred_es:
                    ef_s = self._calendar.add_working_days(pred_es, dep.lag_days)
                    if duration > 0:
                        cand_es = self._calendar.add_working_days(ef_s, -(duration - 1))
                    else:
                        cand_es = ef_s
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
        """
        Enforce actual_start/actual_end onto computed ES/EF.

        Rules:
        - If actual_end exists => EF is fixed to actual_end
            - ES becomes actual_start if present, else EF - duration
        - Else if actual_start exists => ES cannot be earlier than actual_start
            - shift EF accordingly if duration > 0
        """
        a_start = getattr(task, "actual_start", None)
        a_end = getattr(task, "actual_end", None)

        if a_end is not None:
            fixed_ef = a_end
            if a_start is not None:
                fixed_es = a_start
            else:
                if duration_days > 0:
                    fixed_es = self._calendar.add_working_days(fixed_ef, -(duration_days - 1))
                else:
                    fixed_es = fixed_ef
            return fixed_es, fixed_ef

        if a_start is not None:
            if est is None or a_start > est:
                est = a_start
                if duration_days <= 0:
                    eft = est
                else:
                    eft = self._calendar.add_working_days(est, duration_days)

        return est, eft

    def _priority_value(self, task: Task) -> int:
        """
        Lower number = higher priority (so it comes out first in a min-heap).
        Supports:
        - enum with .value
        - int
        - string like 'HIGH', 'MEDIUM', 'LOW' (optional)
        Unknown/missing -> medium (50)
        """
        priority = getattr(task, "priority", None)
        if priority is None:
            return 50
        if hasattr(priority, "value"):
            priority = priority.value
        if isinstance(priority, (int, float)):
            return int(priority)
        if isinstance(priority, str):
            normalized = priority.strip().upper()
            if normalized in ("HIGH", "H"):
                return 10
            if normalized in ("MEDIUM", "M", "NORMAL"):
                return 50
            if normalized in ("LOW", "L"):
                return 90
        return 50
