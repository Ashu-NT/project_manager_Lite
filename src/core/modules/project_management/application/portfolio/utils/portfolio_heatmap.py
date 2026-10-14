"""Pure portfolio heatmap pressure computation.

Shared by the executive and dependency query handlers so pressure scoring
exists exactly once."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from src.core.modules.project_management.application.resources.capacity.resource_load_engine import (
    ResourceLoadEngine,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.application.scheduling.calendars.working_day_snapshot import (
    WorkingDaySnapshotCalendar,
)
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import (
    run_cpm,
)
from src.core.modules.project_management.contracts.reads.portfolio.models.heatmap_facts import (
    HeatmapProjectFacts,
    PortfolioHeatmapFacts,
)
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    TaskStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
)
from src.core.modules.project_management.domain.tasks.hierarchy import (
    select_leaf_dependencies,
    select_leaf_tasks,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)

logger = logging.getLogger(__name__)


def _pressure_label(score: int) -> str:
    if score >= 4:
        return "Hot"
    if score >= 2:
        return "Watch"
    return "Stable"


class PortfolioHeatmapCalculator:
    """Pure per-project pressure computation over pre-read heatmap facts.

    Shared by the executive and dependency query handlers so pressure scoring
    exists exactly once. Carries no permission/scope logic: callers resolve
    scope and read facts first."""

    def __init__(
        self,
        *,
        calendar: CalendarProtocol,
        project_calendar_adapter: ProjectCalendarAdapter,
    ) -> None:
        self._calendar = calendar
        self._project_calendar_adapter = project_calendar_adapter

    def compute_rows(self, facts: PortfolioHeatmapFacts) -> list[PortfolioExecutiveRow]:
        rows: list[PortfolioExecutiveRow] = []
        for project in facts.projects:
            try:
                calendar = self._heatmap_calendar(project)
                critical_tasks, late_tasks = self._heatmap_schedule_counts(
                    project,
                    calendar=calendar,
                )
                peak_utilization = self._heatmap_peak_utilization(
                    project,
                    facts=facts,
                    calendar=calendar,
                )
                cost_variance = self._heatmap_cost_variance(project)
                pressure = 0
                if late_tasks > 0:
                    pressure += 2
                if critical_tasks > 0:
                    pressure += 1
                if peak_utilization >= 120.0:
                    pressure += 2
                elif peak_utilization >= 100.0:
                    pressure += 1
                if cost_variance > 0:
                    pressure += 1
                rows.append(
                    PortfolioExecutiveRow(
                        project_id=project.project_id,
                        project_name=project.project_name,
                        project_status=project.project_status,
                        critical_tasks=critical_tasks,
                        late_tasks=late_tasks,
                        peak_utilization_percent=round(peak_utilization, 1),
                        cost_variance=cost_variance,
                        pressure_score=pressure,
                        pressure_label=_pressure_label(pressure),
                    )
                )
            except Exception:
                logger.warning(
                    "Portfolio heatmap calculation failed project_id=%s",
                    project.project_id,
                    exc_info=True,
                )
                rows.append(
                    PortfolioExecutiveRow(
                        project_id=project.project_id,
                        project_name=project.project_name,
                        project_status=project.project_status,
                        critical_tasks=0,
                        late_tasks=0,
                        peak_utilization_percent=0.0,
                        cost_variance=Decimal(0),
                        pressure_score=0,
                        pressure_label="Stable",
                    )
                )
        return rows

    def _heatmap_schedule_counts(
        self,
        project: HeatmapProjectFacts,
        *,
        calendar: WorkingDaySnapshotCalendar,
    ) -> tuple[int, int]:
        tasks = select_leaf_tasks(self._heatmap_domain_tasks(project))
        if not tasks:
            return 0, 0
        dependencies = select_leaf_dependencies(
            self._heatmap_domain_dependencies(project),
            tasks,
        )
        schedule = run_cpm(
            calendar,
            {task.id: task for task in tasks},
            dependencies,
        ).schedule
        return (
            sum(1 for info in schedule.values() if info.is_critical),
            sum(1 for info in schedule.values() if (info.late_by_days or 0) > 0),
        )

    def _heatmap_peak_utilization(
        self,
        project: HeatmapProjectFacts,
        *,
        facts: PortfolioHeatmapFacts,
        calendar: WorkingDaySnapshotCalendar,
    ) -> float:
        metrics = ResourceLoadEngine.calculate(
            tasks=project.tasks,
            assignments=project.assignments,
            resources=facts.resources,
            working_dates=calendar.working_dates,
        )
        return max((row.utilization_percent for row in metrics), default=0.0)

    def _heatmap_cost_variance(self, project: HeatmapProjectFacts) -> Decimal:
        eac = project.finance.control.estimate_at_completion
        if eac is None:
            return Decimal(0)
        return eac - project.finance.control.approved_budget

    def _heatmap_calendar(self, project: HeatmapProjectFacts) -> WorkingDaySnapshotCalendar:
        values = [
            value
            for task in project.tasks
            for value in (
                task.start_date,
                task.end_date,
                task.actual_start,
                task.actual_end,
                task.deadline,
            )
            if value is not None
        ]
        values.extend(
            value
            for value in (project.finance.project.start_date, project.finance.project.end_date)
            if value is not None
        )
        anchor = min(values) if values else project.finance.as_of
        ceiling = max(values) if values else project.finance.as_of
        work_units = sum(max(int(task.duration_days or 0), 1) for task in project.tasks)
        work_units += sum(abs(row.lag_days) + 2 for row in project.dependencies)
        margin = max(366, work_units * 3 + 30)
        start = anchor - timedelta(days=margin)
        end = ceiling + timedelta(days=margin)
        working_dates = self._project_calendar_adapter.working_day_dates_between(
            project.project_id,
            start,
            end,
        )
        return WorkingDaySnapshotCalendar(start, end, working_dates, self._calendar)

    @staticmethod
    def _heatmap_domain_tasks(project: HeatmapProjectFacts) -> list[Task]:
        return [
            Task(
                id=row.id,
                project_id=row.project_id,
                name=row.name,
                parent_task_id=row.parent_task_id,
                wbs_code=row.wbs_code,
                sort_order=row.sort_order,
                start_date=row.start_date,
                end_date=row.end_date,
                duration_days=row.duration_days,
                status=TaskStatus(row.status),
                priority=row.priority,
                percent_complete=row.percent_complete,
                actual_start=row.actual_start,
                actual_end=row.actual_end,
                deadline=row.deadline,
            )
            for row in project.tasks
        ]

    @staticmethod
    def _heatmap_domain_dependencies(project: HeatmapProjectFacts) -> list[TaskDependency]:
        return [
            TaskDependency(
                id=row.id,
                predecessor_task_id=row.predecessor_task_id,
                successor_task_id=row.successor_task_id,
                dependency_type=DependencyType(row.dependency_type),
                lag_days=row.lag_days,
            )
            for row in project.dependencies
        ]


__all__ = ["PortfolioHeatmapCalculator"]
