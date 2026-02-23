# core/services/baseline_service.py
from typing import Optional, Dict, List

from sqlalchemy.orm import Session

from core.models import ProjectBaseline, BaselineTask, CostType
from core.interfaces import (
    ProjectRepository,
    TaskRepository,
    CostRepository,
    BaselineRepository,
    ProjectResourceRepository,
    ResourceRepository,
)
from core.exceptions import NotFoundError, ValidationError
from core.services.scheduling.engine import SchedulingEngine
from core.services.work_calendar.engine import WorkCalendarEngine


class BaselineService:
    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        cost_repo: CostRepository,
        baseline_repo: BaselineRepository,
        scheduling: SchedulingEngine,
        calendar: WorkCalendarEngine,
        project_resource_repo: ProjectResourceRepository,
        resource_repo: ResourceRepository,
    ):
        self._session: Session = session
        self._projects: ProjectRepository = project_repo
        self._tasks: TaskRepository = task_repo
        self._costs: CostRepository = cost_repo
        self._baselines: BaselineRepository = baseline_repo
        self._sched: SchedulingEngine = scheduling
        self._cal: WorkCalendarEngine = calendar
        self._project_resources: ProjectResourceRepository = project_resource_repo
        self._resources: ResourceRepository = resource_repo

    def create_baseline(self, project_id: str, name: str = "Baseline") -> ProjectBaseline:
        project = self._projects.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        # Ensure we have a computed schedule (CPM provides earliest_start/finish)
        schedule = self._sched.recalculate_project_schedule(project_id)

        tasks = self._tasks.list_by_project(project_id)
        if not tasks:
            raise ValidationError("Cannot baseline: project has no tasks.")

        proj_cur = (getattr(project, "currency", None) or "").upper().strip()

        # -------------------------
        # Planned costs snapshot (baseline budget basis)
        # - exclude manual LABOR CostItems (you compute labor separately)
        # -------------------------
        costs = self._costs.list_by_project(project_id)

        planned_by_task: Dict[str, float] = {}
        planned_unassigned = 0.0

        for c in costs:
            ct = getattr(c, "cost_type", None)
            if ct == CostType.LABOR:
                continue

            amt = float(getattr(c, "planned_amount", 0.0) or 0.0)
            if amt <= 0:
                continue

            if getattr(c, "task_id", None):
                tid = c.task_id
                planned_by_task[tid] = planned_by_task.get(tid, 0.0) + amt
            else:
                planned_unassigned += amt

        # If there are NO planned cost items at all, optionally fall back to project planned budget.
        if (sum(planned_by_task.values()) + planned_unassigned) <= 0.0:
            pb = float(getattr(project, "planned_budget", 0.0) or 0.0)
            if pb > 0:
                planned_unassigned = pb

        # -------------------------
        # Planned labor snapshot (ProjectResource planned_hours × rate)
        # - uses PR override rate/currency else Resource defaults
        # - only includes active PR rows
        # - if project currency is set, only counts labor in that currency (no FX here)
        # -------------------------
        planned_labor_total = 0.0
        pr_rows = self._project_resources.list_by_project(project_id) or []

        for pr in pr_rows:
            if not bool(getattr(pr, "is_active", True)):
                continue

            rid = getattr(pr, "resource_id", None)
            if not rid:
                continue

            res = self._resources.get(rid)
            if not res:
                continue

            ph = float(getattr(pr, "planned_hours", 0.0) or 0.0)
            if ph <= 0:
                continue

            # rate: PR override else resource default
            rate = getattr(pr, "hourly_rate", None)
            if rate is None:
                rate = getattr(res, "hourly_rate", None)
            rate_val = float(rate or 0.0)

            # currency: PR override else resource default
            cur = (getattr(pr, "currency_code", None) or getattr(res, "currency_code", None) or "").upper().strip()

            if proj_cur:
                if not cur:
                    cur = proj_cur
                if cur != proj_cur:
                    # skip mismatched currency without FX conversion
                    continue

            planned_labor_total += ph * rate_val

        baseline = ProjectBaseline.create(project_id, name)

        # -------------------------
        # Build baseline task dates + durations (working days)
        # -------------------------
        task_infos = []
        durations: Dict[str, int] = {}

        for t in tasks:
            info = schedule.get(t.id)
            bs = getattr(info, "earliest_start", None) if info else getattr(t, "start_date", None)
            bf = getattr(info, "earliest_finish", None) if info else getattr(t, "end_date", None)

            if bs and bf:
                dur = max(0, int(self._cal.working_days_between(bs, bf)))
            else:
                dur = max(0, int(getattr(t, "duration_days", 0) or 0))

            durations[t.id] = dur
            task_infos.append((t.id, bs, bf))

        total_dur = sum(durations.values())

        # -------------------------
        # Allocate unassigned planned budget across tasks (duration-weighted, else equal)
        # -------------------------
        alloc_unassigned: Dict[str, float] = {}
        if planned_unassigned > 0 and tasks:
            if total_dur > 0:
                for tid in durations:
                    w = durations[tid] / total_dur if total_dur else 0.0
                    alloc_unassigned[tid] = planned_unassigned * w
            else:
                per = planned_unassigned / float(len(tasks))
                for tid in durations:
                    alloc_unassigned[tid] = per

        # -------------------------
        # Allocate planned labor across tasks (duration-weighted, else equal)
        # -------------------------
        alloc_labor: Dict[str, float] = {}
        if planned_labor_total > 0 and tasks:
            if total_dur > 0:
                for tid in durations:
                    w = durations[tid] / total_dur if total_dur else 0.0
                    alloc_labor[tid] = planned_labor_total * w
            else:
                per = planned_labor_total / float(len(tasks))
                for tid in durations:
                    alloc_labor[tid] = per

        baseline_tasks: List[BaselineTask] = []
        for tid, bs, bf in task_infos:
            dur = durations.get(tid, 0)

            # baseline planned cost = (typed planned cost items for task)
            #                    + (allocated unassigned planned)
            #                    + (allocated planned labor from ProjectResource)
            planned_cost = (
                float(planned_by_task.get(tid, 0.0) or 0.0)
                + float(alloc_unassigned.get(tid, 0.0) or 0.0)
                + float(alloc_labor.get(tid, 0.0) or 0.0)
            )

            baseline_tasks.append(
                BaselineTask.create(
                    baseline_id=baseline.id,
                    task_id=tid,
                    baseline_start=bs,
                    baseline_finish=bf,
                    baseline_duration_days=dur,
                    baseline_planned_cost=planned_cost,
                )
            )

        try:
            self._baselines.add_baseline(baseline)
            self._baselines.add_baseline_tasks(baseline_tasks)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        return baseline

    def get_latest_baseline(self, project_id: str) -> Optional[ProjectBaseline]:
        return self._baselines.get_latest_for_project(project_id)

    def list_baselines(self, project_id: str) -> list[ProjectBaseline]:
        return self._baselines.list_for_project(project_id)

    def delete_baseline(self, baseline_id: str) -> None:
        try:
            self._baselines.delete_baseline(baseline_id)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

