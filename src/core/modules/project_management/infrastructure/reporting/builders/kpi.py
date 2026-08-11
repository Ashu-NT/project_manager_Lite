from __future__ import annotations

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol

from datetime import date, timedelta

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
from src.core.modules.project_management.application.scheduling.services.scheduling_engine import SchedulingEngine
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.modules.project_management.application.resources.resource_load_engine import (
    ResourceLoadEngine,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.modules.project_management.infrastructure.reporting.builders.cost_policy import (
    ReportingCostPolicyMixin,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
)

class ReportingKpiMixin(ReportingCostPolicyMixin):
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _scheduling_engine: SchedulingEngine
    _calendar: CalendarProtocol
    _project_resource_repo: ProjectResourceRepository
    _resource_repo: ResourceRepository
    _assignment_repo: AssignmentRepository

    def get_gantt_data(self, project_id: str) -> list[GanttTaskBar]:
        self._require_view("view gantt report", project_id=project_id)
        """
        Returns a list of GanttTaskBars, ensuring schedule is up to date (CPM).
        """
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id, persist=False)
        # cpm_result: dict[task_id, CPMTaskInfo]
        bars: list[GanttTaskBar] = []

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
                    wbs_code=t.wbs_code,
                )
            )
        # Also include unscheduled tasks (no ES/EF)
        all_tasks = {
            task.id: task
            for task in select_leaf_tasks(self._task_repo.list_by_project(project_id))
        }
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
                        wbs_code=t.wbs_code,
                    )
                )
        return bars

    def get_project_kpis(
        self,
        project_id: str,
        *,
        schedule: dict[str, CPMTaskInfo] | None = None,
    ) -> ProjectKPI:
        self._require_view("view project kpis", project_id=project_id)
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        tasks_total = len(tasks)
        tasks_completed = sum(1 for t in tasks if str(t.status) in ("TaskStatus.DONE", "DONE"))
        tasks_in_progress = sum(1 for t in tasks if str(t.status) in ("TaskStatus.IN_PROGRESS", "IN_PROGRESS"))
        task_blocked = sum(1 for t in tasks if str(t.status) in ("TaskStatus.BLOCKED", "BLOCKED"))
        tasks_not_started = tasks_total - tasks_completed - tasks_in_progress- task_blocked

        # Reuse CPM data for critical & late tasks
        cpm_result: dict[str, CPMTaskInfo] = (
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

    def get_critical_path(self, project_id: str) -> list[CPMTaskInfo]:
        self._require_view("view critical path report", project_id=project_id)
        """
        Return critical tasks in topological order (approximate critical path).
        """
        cpm_result = self._scheduling_engine.recalculate_project_schedule(project_id, persist=False)
        critical = [info for info in cpm_result.values() if info.is_critical]
        # Sort by ES to show actual path order
        critical.sort(key=lambda info: (info.earliest_start or date.min))
        return critical

    def get_resource_load_summary(self, project_id: str) -> list[ResourceLoadRow]:
        self._require_view("view resource load report", project_id=project_id)
        """
        Capacity-aware load summary by resource using peak concurrent allocation.
        """
        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        task_ids = [t.id for t in tasks]
        if not task_ids:
            return []

        assignments = self._assignment_repo.list_by_tasks(task_ids)
        resource_ids = sorted({assignment.resource_id for assignment in assignments})
        resources = tuple(
            resource
            for resource_id in resource_ids
            if (resource := self._resource_repo.get(resource_id)) is not None
        )
        scheduled_ranges = [
            (min(task.start_date, task.end_date), max(task.start_date, task.end_date))
            for task in tasks
            if task.start_date and task.end_date
        ]
        working_dates = (
            self._working_dates_between(
                min(start for start, _end in scheduled_ranges),
                max(end for _start, end in scheduled_ranges),
            )
            if scheduled_ranges
            else frozenset()
        )
        return [
            ResourceLoadRow(
                resource_id=row.resource_id,
                resource_name=row.resource_name,
                total_allocation_percent=row.total_allocation_percent,
                tasks_count=row.tasks_count,
                capacity_percent=row.capacity_percent,
                utilization_percent=row.utilization_percent,
            )
            for row in ResourceLoadEngine.calculate(
                tasks=tasks,
                assignments=assignments,
                resources=resources,
                working_dates=working_dates,
            )
        ]

    def _working_dates_between(self, start: date, end: date) -> frozenset[date]:
        if end < start:
            start, end = end, start
        range_loader = getattr(self._calendar, "working_day_dates_between", None)
        if callable(range_loader):
            return frozenset(range_loader(start, end))
        working_dates: set[date] = set()
        cur = start
        while cur <= end:
            if self._calendar.is_working_day(cur):
                working_dates.add(cur)
            cur += timedelta(days=1)
        return frozenset(working_dates)
