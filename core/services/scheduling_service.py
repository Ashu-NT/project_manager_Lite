# core/services/scheduling_service.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import date
import heapq
from sqlalchemy.orm import Session

from ..models import Task, TaskDependency, DependencyType
from ..interfaces import TaskRepository, DependencyRepository
from ..exceptions import BusinessRuleError, ValidationError
from .work_calendar_engine import WorkCalendarEngine


@dataclass
class CPMTaskInfo:
    task: Task
    earliest_start: Optional[date]
    earliest_finish: Optional[date]
    latest_start: Optional[date]
    latest_finish: Optional[date]
    total_float_days: Optional[int]
    is_critical: bool
    deadline: Optional[date] = None
    late_by_days: Optional[int] = None


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
        self._session = session
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._calendar = calendar

    # Public API
   
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

        # Filter dependencies to this project's tasks only
        deps = [
            d for d in deps
            if d.predecessor_task_id in tasks_by_id and d.successor_task_id in tasks_by_id
        ]
        
        # Build graph and indegree for topological sort
        graph_succ: Dict[str, List[TaskDependency]] = {}
        indegree: Dict[str, int] = {t.id: 0 for t in tasks}

        for d in deps:
            graph_succ.setdefault(d.predecessor_task_id, []).append(d)
            indegree[d.successor_task_id] += 1
          
        # Kahn's algorithm, but priority-aware & deterministic
         # Use a min-heap keyed by (priority_value, task_name, task_id)
         
        heap: list[tuple[int, str, str]] = []
        for tid, deg in indegree.items():
             if deg == 0:
                 t = tasks_by_id[tid]
                 heapq.heappush(heap, (self._priority_value(t), (getattr(t, "name", "") or ""), tid))
 
        topo_order: List[str] = []
        while heap:
            _p, _nm, tid = heapq.heappop(heap)
            topo_order.append(tid)
            for dep in graph_succ.get(tid, []):
                succ = dep.successor_task_id
                indegree[succ] -= 1
                if indegree[succ] == 0:
                    t = tasks_by_id[succ]
                    heapq.heappush(heap, (self._priority_value(t), (getattr(t, "name", "") or ""),succ))

        if len(topo_order) != len(tasks):
            raise BusinessRuleError("Cannot schedule project: circular dependency detected.", code="SCHEDULE_CYCLE")

        # Group dependencies by successor and by predecessor
        deps_by_successor: Dict[str, List[TaskDependency]] = {}
        deps_by_predecessor: Dict[str, List[TaskDependency]] = {}
        for d in deps:
            deps_by_successor.setdefault(d.successor_task_id, []).append(d)
            deps_by_predecessor.setdefault(d.predecessor_task_id, []).append(d)

        # Forward pass: ES/EF
        es: Dict[str, Optional[date]] = {t.id: None for t in tasks}
        ef: Dict[str, Optional[date]] = {t.id: None for t in tasks}

        for task_id in topo_order:
            task = tasks_by_id[task_id]
            incoming = deps_by_successor.get(task_id, [])
            duration = task.duration_days or 0

            if duration <= 0:
                est, eft = self._compute_dates_milestone(task, incoming, es, ef)
            else:
                est, eft = self._compute_dates_with_duration(task, incoming, es, ef, duration)

            est , eft = self._apply_actual_constraints(task, est, eft, int(duration or 0))
            
            es[task_id] = est
            ef[task_id] = eft

        # Project early finish = max EF
        project_ef_dates = [d for d in ef.values() if d is not None]
        if not project_ef_dates:
            raise ValidationError("No computed finish dates; ensure tasks have durations or start dates.")
        project_early_finish = max(project_ef_dates)

        # Backward pass: LS/LF
        ls: Dict[str, Optional[date]] = {t.id: None for t in tasks}
        lf: Dict[str, Optional[date]] = {t.id: None for t in tasks}

        # Start from "end" tasks (no successors)
        end_tasks = [tid for tid in tasks_by_id.keys() if tid not in deps_by_predecessor]
        for tid in end_tasks:
            duration = tasks_by_id[tid].duration_days or 0
            if duration <= 0:
                lf[tid] = project_early_finish
                ls[tid] = project_early_finish
            else:
                lf[tid] = project_early_finish
                ls[tid] = self._calendar.add_working_days(project_early_finish, - (duration-1))

        # Propagate backwards along reversed topo
        for task_id in reversed(topo_order):
            outgoing = deps_by_predecessor.get(task_id, [])
            if not outgoing:
                # already set above (end tasks), or maybe isolated
                if ls[task_id] is None and es[task_id] is not None:
                    # no constraints from successors; LS = ES, LF = EF
                    ls[task_id] = es[task_id]
                    lf[task_id] = ef[task_id]
                continue

            # Combine constraints from all successors
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
                    # ES_s >= EF_p  lag  =>  LF_p <= LS_s - lag
                    if succ_ls is not None:
                        cand_lf = self._calendar.add_working_days(succ_ls, -dep.lag_days)
                        cand_lf_dates.append(cand_lf)

                elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                    # EF_s >= EF_p  lag  =>  LF_p <= LF_s - lag
                    if succ_lf is not None:
                        cand_lf = self._calendar.add_working_days(succ_lf, -dep.lag_days)
                        cand_lf_dates.append(cand_lf)

                elif dep.dependency_type == DependencyType.START_TO_START:
                    # ES_s >= ES_p  lag  =>  LS_p <= LS_s - lag
                    if succ_ls is not None:
                        cand_ls = self._calendar.add_working_days(succ_ls, -dep.lag_days)
                        cand_ls_dates.append(cand_ls)

                elif dep.dependency_type == DependencyType.START_TO_FINISH:
                    # EF_s >= ES_p  lag  =>  ES_p <= LF_s - lag
                    if succ_lf is not None:
                        cand_ls = self._calendar.add_working_days(succ_lf, -dep.lag_days)
                        cand_ls_dates.append(cand_ls)

            # Resolve LS/LF from collected candidates
            if cand_lf_dates:
                lf_candidate = min(cand_lf_dates)
                lf[task_id] = lf_candidate
                if duration > 0:
                    ls[task_id] = self._calendar.add_working_days(lf_candidate, - (duration-1))
                else:
                    ls[task_id] = lf_candidate
            elif cand_ls_dates:
                ls_candidate = min(cand_ls_dates)
                ls[task_id] = ls_candidate
                if duration > 0:
                    lf[task_id] = self._calendar.add_working_days(ls_candidate, (duration - 1))
                else:
                    lf[task_id] = ls_candidate
            else:
                # no constraints (shouldn't really happen if outgoing exists),
                # fallback to ES/EF if they exist
                if es[task_id] is not None:
                    ls[task_id] = es[task_id]
                    lf[task_id] = ef[task_id]

        # Build CPMTaskInfo, update tasks with ES/EF
        result: Dict[str, CPMTaskInfo] = {}
        for tid, task in tasks_by_id.items():
            est = es[tid]
            eft = ef[tid]
            lst = ls[tid]
            lft = lf[tid]

           # Update task with ES/EF
            if getattr(task,"actual_start",None) is None:
                task.start_date = est
            if getattr(task,"actual_end",None) is None:
                task.end_date = eft

            # Compute total float (in working days)
            if est is not None and lst is not None:
                if lst < est:
                    total_float = 0
                else:
                    days = self._calendar.working_days_between(est, lst)
                    # working_days_between is inclusive; slack should be zero
                    total_float = max(0, days - 1)
            else:
                total_float = None

            is_critical = total_float == 0 if total_float is not None else False
            # Deadline and late_by_days
            late_by = None
            if task.deadline and eft:
                if eft > task.deadline:
                    # working days betwwen deadline1 and EF
                    late_by = self._calendar.working_days_between(
                        self._calendar.add_working_days(task.deadline,1),
                        eft,
                    )
            
            result[tid] = CPMTaskInfo(
                task=task,
                earliest_start=est,
                earliest_finish=eft,
                latest_start=lst,
                latest_finish=lft,
                total_float_days=total_float,
                is_critical=is_critical,
                deadline=task.deadline,
                late_by_days=late_by,
            )

        # Persist updated tasks
        try:
            for info in result.values():
                self._task_repo.update(info.task)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e

        return result

    # Internal helpers (forward pass)

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
                    candidate_es.append(
                        self._calendar.add_working_days(pred_ef, dep.lag_days)
                    )

            elif dep.dependency_type == DependencyType.START_TO_START:
                if pred_es:
                    candidate_es.append(
                        self._calendar.add_working_days(pred_es, dep.lag_days)
                    )

            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                # EF_s >= EF_p  lag => ES_s >= EF_p  lag - duration_s
                if pred_ef:
                    ef_s = self._calendar.add_working_days(pred_ef, dep.lag_days)
                    if duration > 0:
                        cand_es = self._calendar.add_working_days(ef_s, -(duration-1))
                    else:
                        cand_es = ef_s 
                    candidate_es.append(cand_es)

            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                # EF_s >= ES_p  lag => ES_s >= ES_p  lag - duration_s
                if pred_es:
                    ef_s = self._calendar.add_working_days(pred_es, dep.lag_days)
                    if duration > 0:
                        cand_es = self._calendar.add_working_days(ef_s, -(duration-1))
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
            task,
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
    
            # Finished tasks: lock EF (and ES if possible)
            if a_end is not None:
                fixed_ef = a_end
                if a_start is not None:
                    fixed_es = a_start
                else:
                    if duration_days > 0:
                        fixed_es = self._calendar.add_working_days(fixed_ef, - (duration_days - 1))
                    else:
                        fixed_es = fixed_ef
                return fixed_es, fixed_ef
    
            # Started tasks: ES cannot be earlier than actual_start
            if a_start is not None:
                if est is None or a_start > est:
                    est = a_start
                    if duration_days <= 0:
                        eft = est
                    else:
                        eft = self._calendar.add_working_days(est, duration_days)
    
            return est, eft   

    def _priority_value(self, task) -> int:
         """
         Lower number = higher priority (so it comes out first in a min-heap).
         Supports:
         - enum with .value
         - int
         - string like 'HIGH', 'MEDIUM', 'LOW' (optional)
         Unknown/missing -> medium (50)
         """
         p = getattr(task, "priority", None)
         if p is None:
             return 50
         if hasattr(p, "value"):
             p = p.value
         if isinstance(p, (int, float)):
             return int(p)
         if isinstance(p, str):
             s = p.strip().upper()
             if s in ("HIGH", "H"):
                 return 10
             if s in ("MEDIUM", "M", "NORMAL"):
                 return 50
             if s in ("LOW", "L"):
                 return 90
         return 50
