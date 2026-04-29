from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.cost_calendar import CostRepository
from src.core.modules.project_management.application.scheduling import (
    CPMTaskInfo,
    SchedulingEngine,
    WorkCalendarEngine,
)
from src.core.modules.project_management.infrastructure.reporting.cost_policy import (
    ReportingCostPolicyMixin,
)
from src.core.modules.project_management.infrastructure.reporting.models import (
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)


class ReportingKpiMixin(ReportingCostPolicyMixin):
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _scheduling_engine: SchedulingEngine
    _calendar: WorkCalendarEngine
    _cost_repo: CostRepository
    _project_resource_repo: ProjectResourceRepository
    _resource_repo: ResourceRepository
    _assignment_repo: AssignmentRepository

    def get_gantt_data(self, project_id: str) -> List[GanttTaskBar]:
        self._require_view("view gantt report", project_id=project_id)
        """
        Returns a list of GanttTaskBars, ensuring schedule is up to date (CPM).
        """
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id, persist=False)
        # cpm_result: Dict[task_id, CPMTaskInfo]
        bars: List[GanttTaskBar] = []

        for tid, info in cpm_result.items():
            t = info.task
            bars.append(
                GanttTaskBar(
                    task_id=t.id,
                    name=t.name,
                    start=info.earliest_start,
                    end=info.earliest_finish,
                    is_critical=info.is_critical,
                    percent_complete=t.percent_complete or 0.0,
                    status=t.status.value if hasattr(t.status, "value") else str(t.status),
                )
            )
        # Also include unscheduled tasks (no ES/EF)
        all_tasks = {t.id: t for t in self._task_repo.list_by_project(project_id)}
        for tid, t in all_tasks.items():
            if tid not in cpm_result:
                bars.append(
                    GanttTaskBar(
                        task_id=t.id,
                        name=t.name,
                        start=t.start_date,
                        end=t.end_date,
                        is_critical=False,
                        percent_complete=t.percent_complete or 0.0,
                        status=t.status.value if hasattr(t.status, "value") else str(t.status),
                    )
                )
        return bars

    def get_project_kpis(
        self,
        project_id: str,
        *,
        schedule: Dict[str, CPMTaskInfo] | None = None,
    ) -> ProjectKPI:
        self._require_view("view project kpis", project_id=project_id)
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        tasks = self._task_repo.list_by_project(project_id)
        tasks_total = len(tasks)
        tasks_completed = sum(1 for t in tasks if str(t.status) in ("TaskStatus.DONE", "DONE"))
        tasks_in_progress = sum(1 for t in tasks if str(t.status) in ("TaskStatus.IN_PROGRESS", "IN_PROGRESS"))
        task_blocked = sum(1 for t in tasks if str(t.status) in ("TaskStatus.BLOCKED", "BLOCKED"))
        tasks_not_started = tasks_total - tasks_completed - tasks_in_progress- task_blocked

        # Reuse CPM data for critical & late tasks
        cpm_result: Dict[str, CPMTaskInfo] = (
            schedule
            if schedule is not None
            else self._scheduling_engine.recalculate_project_schedule(
                project_id,
                persist=False,
            )
        )
        critical_tasks = sum(1 for info in cpm_result.values() if info.is_critical)
        late_tasks = sum(
            1
            for info in cpm_result.values()
            if info.late_by_days is not None and info.late_by_days > 0
        )

        # Project dates & duration
        start_date = project.start_date
        end_date = project.end_date
        duration_working_days = None
        if start_date and end_date:
            duration_working_days = self._calendar.working_days_between(start_date, end_date)

        # Cost summary (shared policy used by KPI, EVM, cost breakdown, and Cost tab)
        cost_snapshot = self._build_cost_policy_snapshot(project_id=project_id)
        total_planned = self._sum_bucket_map(
            cost_snapshot.planned_map,
            cost_snapshot.project_currency,
        )
        total_committed = self._sum_bucket_map(
            cost_snapshot.committed_map,
            cost_snapshot.project_currency,
        )
        total_actual = self._sum_bucket_map(
            cost_snapshot.actual_map,
            cost_snapshot.project_currency,
        )

        cost_variance = float(total_actual - total_planned)
        committed_variance = float(total_committed - total_planned)

        return ProjectKPI(
            project_id=project.id,
            name=project.name,
            start_date=start_date,
            end_date=end_date,
            duration_working_days=duration_working_days,
            tasks_total=tasks_total,
            tasks_completed=tasks_completed,
            tasks_in_progress=tasks_in_progress,
            task_blocked=task_blocked,
            tasks_not_started=tasks_not_started,
            critical_tasks=critical_tasks,
            late_tasks=late_tasks,

            total_planned_cost=total_planned,
            total_committed_cost= total_committed,
            total_actual_cost=total_actual,
            cost_variance=cost_variance,
            committment_variance= committed_variance,
        )

    def get_critical_path(self, project_id: str) -> List[CPMTaskInfo]:
        self._require_view("view critical path report", project_id=project_id)
        """
        Return critical tasks in topological order (approximate critical path).
        """
        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id, persist=False)
        critical = [info for info in cpm_result.values() if info.is_critical]
        # Sort by ES to show actual path order
        critical.sort(key=lambda info: (info.earliest_start or date.min))
        return critical

    def get_resource_load_summary(self, project_id: str) -> List[ResourceLoadRow]:
        self._require_view("view resource load report", project_id=project_id)
        """
        Capacity-aware load summary by resource using peak concurrent allocation.
        """
        tasks = self._task_repo.list_by_project(project_id)
        task_ids = [t.id for t in tasks]
        if not task_ids:
            return []

        assignments = self._assignment_repo.list_by_tasks(task_ids)
        tasks_by_id = {t.id: t for t in tasks}
        # group by resource
        load_by_res: Dict[str, Tuple[float, int, float]] = {}
        daily_by_res: Dict[str, Dict[date, float]] = {}
        for a in assignments:
            rid = a.resource_id
            _peak, count, unscheduled = load_by_res.get(rid, (0.0, 0, 0.0))
            alloc = float(a.allocation_percent or 0.0)
            count += 1
            task = tasks_by_id.get(a.task_id)
            ts = getattr(task, "start_date", None) if task is not None else None
            te = getattr(task, "end_date", None) if task is not None else None
            if alloc > 0.0 and ts and te:
                bucket = daily_by_res.setdefault(rid, {})
                for d in self._iter_workdays(ts, te):
                    bucket[d] = bucket.get(d, 0.0) + alloc
            elif alloc > 0.0:
                # Unscheduled assignments are treated conservatively as additional risk.
                unscheduled += alloc
            load_by_res[rid] = (0.0, count, unscheduled)

        rows: List[ResourceLoadRow] = []
        for res_id, (_unused_peak, count, unscheduled_alloc) in load_by_res.items():
            peak_daily_alloc = max(daily_by_res.get(res_id, {}).values(), default=0.0)
            total_alloc = float(peak_daily_alloc + unscheduled_alloc)
            res = self._resource_repo.get(res_id)
            name = res.name if res else "<unknown>"
            capacity = float(getattr(res, "capacity_percent", 100.0) or 100.0) if res else 100.0
            if capacity <= 0.0:
                capacity = 100.0
            utilization = (float(total_alloc) / capacity) * 100.0
            rows.append(
                ResourceLoadRow(
                    resource_id=res_id,
                    resource_name=name,
                    total_allocation_percent=total_alloc,
                    tasks_count=count,
                    capacity_percent=capacity,
                    utilization_percent=utilization,
                )
            )

        # Sort by highest utilization pressure.
        rows.sort(
            key=lambda r: (r.utilization_percent, r.total_allocation_percent),
            reverse=True,
        )
        return rows

    def _iter_workdays(self, start: date, end: date):
        if end < start:
            start, end = end, start
        cur = start
        while cur <= end:
            if self._calendar.is_working_day(cur):
                yield cur
            cur += timedelta(days=1)
