from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

from core.exceptions import NotFoundError
from core.interfaces import (
    AssignmentRepository,
    CostRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.services.reporting.cost_policy import ReportingCostPolicyMixin
from core.services.reporting.models import GanttTaskBar, ProjectKPI, ResourceLoadRow
from core.services.scheduling.engine import CPMTaskInfo, SchedulingEngine
from core.services.work_calendar.engine import WorkCalendarEngine


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
        """
        Returns a list of GanttTaskBars, ensuring schedule is up to date (CPM).
        """
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id)
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

    def get_project_kpis(self, project_id: str) -> ProjectKPI:
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
        cpm_result: Dict[str, CPMTaskInfo] = self._scheduling_engine.recalculate_project_schedule(project_id)
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
        """
        Return critical tasks in topological order (approximate critical path).
        """
        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id)
        critical = [info for info in cpm_result.values() if info.is_critical]
        # Sort by ES to show actual path order
        critical.sort(key=lambda info: (info.earliest_start or date.min))
        return critical

    def get_resource_load_summary(self, project_id: str) -> List[ResourceLoadRow]:
        """
        Simple resource load: for a given project, sum allocation_percent across its tasks.
        Not a time-phased histogram, but a quick overview.
        """
        tasks = self._task_repo.list_by_project(project_id)
        task_ids = [t.id for t in tasks]
        if not task_ids:
            return []

        assignments = self._assignment_repo.list_by_tasks(task_ids)
        # group by resource
        load_by_res: Dict[str, Tuple[float, int]] = {}
        for a in assignments:
            total, count = load_by_res.get(a.resource_id, (0.0, 0))
            total += a.allocation_percent or 0.0
            count += 1
            load_by_res[a.resource_id] = (total, count)

        rows: List[ResourceLoadRow] = []
        for res_id, (total_alloc, count) in load_by_res.items():
            res = self._resource_repo.get(res_id)
            name = res.name if res else "<unknown>"
            rows.append(
                ResourceLoadRow(
                    resource_id=res_id,
                    resource_name=name,
                    total_allocation_percent=total_alloc,
                    tasks_count=count,
                )
            )

        # Sort by highest total allocation
        rows.sort(key=lambda r: r.total_allocation_percent, reverse=True)
        return rows
