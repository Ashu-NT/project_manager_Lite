# src/core/modules/project_management/application/scheduling/engine.py
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.calendar_resolver import (
    CalendarResolver,
)
from src.core.modules.project_management.application.scheduling.constraint_validator import (
    ConstraintType,
)
from src.core.modules.project_management.application.scheduling.date_compute import (
    compute_task_dates_common,
)
from src.core.modules.project_management.application.scheduling.graph import (
    build_project_dependency_graph,
)
from src.core.modules.project_management.application.scheduling.leveling_service import (
    ResourceLevelingMixin,
)
from src.core.modules.project_management.application.scheduling.models import CPMTaskInfo
from src.core.modules.project_management.application.scheduling.passes import (
    run_backward_pass,
    run_forward_pass,
)
from src.core.modules.project_management.application.scheduling.results import (
    build_schedule_result,
)
from src.core.modules.project_management.application.scheduling.work_calendar_engine import (
    WorkCalendarEngine,
)
from src.core.modules.project_management.application.scheduling.project_calendar_adapter import (
    BoundProjectCalendar,
    ProjectCalendarAdapter,
)


class SchedulingEngine(ResourceLevelingMixin):
    """
    CPM-style scheduling engine:
    - Forward pass: ES/EF
    - Backward pass: LS/LF
    - FS, FF, SS, SF with lag_days
    - Scheduling constraints: MSO, MFO, SNET, FNET applied during forward pass
    - Per-resource calendar overrides via CalendarResolver
    """

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        calendar: WorkCalendarEngine,
        assignment_repo: AssignmentRepository | None = None,
        resource_repo: ResourceRepository | None = None,
        calendar_resolver: CalendarResolver | None = None,
        resource_calendar_map: Dict[str, WorkCalendarEngine] | None = None,
        project_calendar_adapter: ProjectCalendarAdapter | None = None,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._base_calendar: WorkCalendarEngine = calendar  # never mutated; restored after each run
        self._calendar: WorkCalendarEngine = calendar
        self._task_calendar: WorkCalendarEngine = calendar  # per-task override, reset each pass
        self._assignment_repo: AssignmentRepository | None = assignment_repo
        self._resource_repo: ResourceRepository | None = resource_repo
        self._calendar_resolver: CalendarResolver | None = calendar_resolver
        self._resource_calendar_map: Dict[str, WorkCalendarEngine] = resource_calendar_map or {}
        self._task_primary_resource: Dict[str, str] = {}  # task_id → resource_id, pre-loaded per run
        self._project_calendar_adapter: ProjectCalendarAdapter | None = project_calendar_adapter

    def recalculate_project_schedule(
        self,
        project_id: str,
        *,
        persist: bool = True,
    ) -> Dict[str, CPMTaskInfo]:
        """
        Full CPM calculation for a project:
        - computes ES/EF (forward) and LS/LF (backward)
        - applies scheduling constraints (MSO/MFO/SNET/FNET) during forward pass
        - applies per-resource calendar overrides when CalendarResolver is wired
        - updates Task.start_date / Task.end_date from ES/EF
        - returns CPMTaskInfo per task
        """
        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return {}

        # If a project has an enterprise calendar assignment, bind the adapter so all
        # CPM arithmetic uses that calendar instead of the global WorkCalendarEngine.
        if self._project_calendar_adapter is not None:
            try:
                bound = self._project_calendar_adapter.bind_for_project(project_id)
                if bound is not None:
                    self._calendar = bound
                    self._task_calendar = bound
            except Exception:
                pass  # fall back to default WorkCalendarEngine

        tasks_by_id: Dict[str, Task] = {t.id: t for t in tasks}
        deps: List[TaskDependency] = self._dependency_repo.list_by_project(project_id)

        # Pre-load task→primary_resource for per-task calendar resolution
        if self._calendar_resolver and self._assignment_repo and self._resource_calendar_map:
            task_ids = list(tasks_by_id)
            assignments = self._assignment_repo.list_by_tasks(task_ids)
            self._task_primary_resource = {}
            for a in assignments:
                if a.task_id not in self._task_primary_resource:
                    self._task_primary_resource[a.task_id] = a.resource_id

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

        # Reset per-run state — restore base calendar so multi-project calls don't cross-contaminate
        self._task_primary_resource = {}
        self._calendar = self._base_calendar
        self._task_calendar = self._base_calendar

        if persist:
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
        self._task_calendar = self._resolve_task_calendar(task.id)
        est, eft = compute_task_dates_common(
            task=task,
            incoming_deps=incoming_deps,
            es=es,
            ef=ef,
            compute_milestone=self._compute_dates_milestone,
            compute_with_duration=self._compute_dates_with_duration,
            apply_actual_constraints=self._apply_actual_constraints,
        )
        return self._apply_scheduling_constraints(task, est, eft)

    def _resolve_task_calendar(self, task_id: str) -> WorkCalendarEngine:
        """Return the highest-priority calendar for a task's primary resource."""
        if not self._calendar_resolver or not self._resource_calendar_map:
            return self._calendar
        resource_id = self._task_primary_resource.get(task_id)
        if not resource_id:
            return self._calendar
        resource_cal = self._resource_calendar_map.get(resource_id)
        return self._calendar_resolver.resolve_for_resource(
            resource_calendar=resource_cal,
            project_calendar=self._calendar,
        )

    def _apply_scheduling_constraints(
        self,
        task: Task,
        est: Optional[date],
        eft: Optional[date],
    ) -> tuple[Optional[date], Optional[date]]:
        """
        Apply forward-pass scheduling constraints (MSO, MFO, SNET, FNET).

        SNLT, FNLT, DEADLINE are validation-only — they are reported by
        ConstraintValidator but do not drive the forward-pass schedule.
        Skipped entirely when task.actual_end is set (task is done).
        """
        if getattr(task, "actual_end", None) is not None:
            return est, eft

        raw_ct = getattr(task, "constraint_type", None)
        cd: Optional[date] = getattr(task, "constraint_date", None)
        if raw_ct is None or cd is None:
            return est, eft

        try:
            ct = ConstraintType(str(raw_ct)) if not isinstance(raw_ct, ConstraintType) else raw_ct
        except ValueError:
            return est, eft

        duration = int(task.duration_days or 0)
        cal = self._task_calendar

        if ct == ConstraintType.MUST_START_ON:
            est = cd
            eft = cal.add_working_days(cd, duration) if duration > 0 else cd

        elif ct == ConstraintType.MUST_FINISH_ON:
            eft = cd
            est = cal.add_working_days(cd, -(duration - 1)) if duration > 0 else cd

        elif ct == ConstraintType.START_NO_EARLIER_THAN:
            if est is None or est < cd:
                est = cd
                eft = cal.add_working_days(cd, duration) if duration > 0 else cd

        elif ct == ConstraintType.FINISH_NO_EARLIER_THAN:
            if eft is None or eft < cd:
                eft = cd
                est = cal.add_working_days(cd, -(duration - 1)) if duration > 0 else cd

        return est, eft

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
                    candidates.append(self._task_calendar.add_working_days(pred_ef, dep.lag_days + 2))
            elif dep.dependency_type == DependencyType.START_TO_START:
                if pred_es:
                    candidates.append(self._task_calendar.add_working_days(pred_es, dep.lag_days))
            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                if pred_ef:
                    candidates.append(self._task_calendar.add_working_days(pred_ef, dep.lag_days))
            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                if pred_es:
                    candidates.append(self._task_calendar.add_working_days(pred_es, dep.lag_days))

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
                eft = self._task_calendar.add_working_days(est, duration)
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
                    candidate_es.append(self._task_calendar.add_working_days(pred_ef, dep.lag_days + 2))

            elif dep.dependency_type == DependencyType.START_TO_START:
                if pred_es:
                    candidate_es.append(self._task_calendar.add_working_days(pred_es, dep.lag_days))

            elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
                if pred_ef:
                    ef_s = self._task_calendar.add_working_days(pred_ef, dep.lag_days)
                    if duration > 0:
                        cand_es = self._task_calendar.add_working_days(ef_s, -(duration - 1))
                    else:
                        cand_es = ef_s
                    candidate_es.append(cand_es)

            elif dep.dependency_type == DependencyType.START_TO_FINISH:
                if pred_es:
                    ef_s = self._task_calendar.add_working_days(pred_es, dep.lag_days)
                    if duration > 0:
                        cand_es = self._task_calendar.add_working_days(ef_s, -(duration - 1))
                    else:
                        cand_es = ef_s
                    candidate_es.append(cand_es)

        if not candidate_es:
            if task.start_date:
                est = task.start_date
                eft = self._task_calendar.add_working_days(est, duration)
                return est, eft
            return None, None

        est = max(candidate_es)
        eft = self._task_calendar.add_working_days(est, duration)
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
                    fixed_es = self._task_calendar.add_working_days(fixed_ef, -(duration_days - 1))
                else:
                    fixed_es = fixed_ef
            return fixed_es, fixed_ef

        if a_start is not None:
            if est is None or a_start > est:
                est = a_start
                if duration_days <= 0:
                    eft = est
                else:
                    eft = self._task_calendar.add_working_days(est, duration_days)

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
