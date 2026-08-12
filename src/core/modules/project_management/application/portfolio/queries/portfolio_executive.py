from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from src.core.modules.project_management.application.resources.resource_load_engine import (
    ResourceLoadEngine,
)
from src.core.modules.project_management.application.scheduling.calendars.working_day_snapshot import (
    WorkingDaySnapshotCalendar,
)
from src.core.modules.project_management.application.scheduling.cpm.cpm_calculator import (
    CPMCalculator,
)
from src.core.modules.project_management.contracts.reads.portfolio.models.heatmap_facts import (
    HeatmapProjectFacts,
    PortfolioHeatmapFacts,
)
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioRecentAction,
)
from src.core.modules.project_management.domain.tasks.hierarchy import (
    select_leaf_dependencies,
    select_leaf_tasks,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission


logger = logging.getLogger(__name__)


class PortfolioExecutiveQueryMixin:
    def list_portfolio_heatmap(self) -> list[PortfolioExecutiveRow]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio executive heatmap")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view portfolio executive heatmap"
        )
        accessible_project_ids = tuple(project.id for project in self._accessible_projects())
        facts = self._heatmap_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_ids=accessible_project_ids,
            as_of=date.today(),
        )
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
                        pressure_label=self._pressure_label(pressure),
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
                        cost_variance=Decimal("0"),
                        pressure_score=0,
                        pressure_label="Stable",
                    )
                )
        return sorted(
            rows,
            key=lambda row: (-row.pressure_score, -row.late_tasks, row.project_name.lower()),
        )

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
        schedule = CPMCalculator(calendar).calculate(
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
            return Decimal("0")
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

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        require_permission(self._user_session, "portfolio.read", operation_label="view recent pm actions")
        accessible_projects = {project.id: project for project in self._accessible_projects()}
        if not accessible_projects:
            return []
        _PM_ENTITY_TYPES = {
            "project", "task", "project_baseline", "approval_request",
            "timesheet_period", "project_membership", "portfolio",
        }
        rows = []
        for row in self._audit_repo.list_recent(limit=max(limit * 4, 50)):
            entity_type = str(getattr(row, "entity_type", "") or "").strip().lower()
            if entity_type not in _PM_ENTITY_TYPES:
                continue
            project_id = str(
                getattr(row, "project_id", None)
                or getattr(row, "entity_parent_id", None)
                or (getattr(row, "metadata", None) or {}).get("project_id")
                or ""
            ).strip()
            project = accessible_projects.get(project_id)
            if project is None:
                continue
            action = str(
                getattr(row, "action", None)
                or (getattr(row, "metadata", None) or {}).get("action")
                or f"{entity_type}.{getattr(row, 'operation', 'update')}"
                or ""
            )
            rows.append(
                PortfolioRecentAction(
                    occurred_at=getattr(row, "occurred_at", None) or getattr(row, "timestamp", None),
                    project_name=project.name,
                    action_label=self._audit_action_label(action),
                    actor_username=str(getattr(row, "actor_username", "") or ""),
                    summary=self._audit_summary(row),
                )
            )
            if len(rows) >= limit:
                break
        return rows


__all__ = ["PortfolioExecutiveQueryMixin"]
