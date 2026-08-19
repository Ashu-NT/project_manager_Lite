from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from src.core.modules.project_management.application.common.pagination import PaginatedResult
from src.core.modules.project_management.application.resources.resource_load_engine import (
    ResourceLoadEngine,
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
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.domain.enums import DependencyType, ProjectStatus, TaskStatus
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
from src.core.platform.common.exceptions import BusinessRuleError


logger = logging.getLogger(__name__)

# Matches the existing watchlist convention used by the Dashboard's own
# top_n tables (critical_watchlist / milestone_health) — see
# api/desktop/dashboard/builders/operational_table_builder.py.
TOP_AT_RISK_PROJECTS_LIMIT = 8

_HEATMAP_BROWSE_SORT_KEYS = {"projectName", "statusLabel"}


class PortfolioExecutiveQueryMixin:
    def list_portfolio_heatmap(self, *, limit: int | None = None) -> list[PortfolioExecutiveRow]:
        """Authoritative heatmap ranking over the COMPLETE accessible project
        scope. With limit=None (default) this returns every accessible
        project and is what list_project_dependencies() enriches against —
        do not change that default. Pass limit= to use this as the bounded
        "Top At-Risk Projects" projection (collection_semantics=top_n);
        that ranking is always computed from the full scope, never from a
        paginated page, so page_size can never change which projects appear.
        """
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
        rows = sorted(
            self._compute_heatmap_rows(facts),
            key=lambda row: (-row.pressure_score, -row.late_tasks, row.project_name.lower()),
        )
        if limit is not None:
            rows = rows[: max(0, int(limit))]
        return rows

    def list_top_at_risk_projects(
        self, *, limit: int = TOP_AT_RISK_PROJECTS_LIMIT
    ) -> list[PortfolioExecutiveRow]:
        """Bounded/top_n analytical projection: ranks pressure across the
        complete authorized project scope, then truncates. Never derive this
        from a paginated Heatmap page."""
        return self.list_portfolio_heatmap(limit=limit)

    def list_portfolio_heatmap_page(
        self,
        *,
        search_text: str = "",
        status: ProjectStatus | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> PaginatedResult[PortfolioExecutiveRow]:
        """Authoritative server-paginated Heatmap browse. Project selection
        (scope/search/status/sort/page) happens in SQL via the shared
        project catalog reader BEFORE any per-project pressure computation
        runs — pressure is computed only for the rows on the returned page,
        never for the full accessible scope. Sorting is restricted to
        genuinely SQL-authoritative columns (project name/status); pressure
        is display-only here and is never a sortable key for this method —
        use list_top_at_risk_projects() for a global pressure ranking.
        """
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio executive heatmap")
        if self._project_catalog_reader is None:
            raise BusinessRuleError(
                "Portfolio heatmap pagination requires a project catalog reader.",
                code="PORTFOLIO_HEATMAP_PAGE_READER_REQUIRED",
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view portfolio executive heatmap"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(sorted(self._user_session.project_ids_for("project.read")))
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys=_HEATMAP_BROWSE_SORT_KEYS,
            default_key="projectName",
        )
        project_page = self._project_catalog_reader.read_page(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            allowed_project_ids=allowed_project_ids,
            search_text=search_text,
            status=status,
            page=page,
            page_size=page_size,
            sort=sort,
        )
        page_project_ids = tuple(item.project.id for item in project_page.items)
        if not page_project_ids:
            return PaginatedResult(items=[], page=page, page_size=page_size, total=project_page.filtered_total)
        facts = self._heatmap_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_ids=page_project_ids,
            as_of=date.today(),
        )
        rows_by_id = {row.project_id: row for row in self._compute_heatmap_rows(facts)}
        # Preserve the SQL-determined order — never re-sort by pressure here.
        ordered_rows = [rows_by_id[project_id] for project_id in page_project_ids if project_id in rows_by_id]
        return PaginatedResult(
            items=ordered_rows,
            page=page,
            page_size=page_size,
            total=project_page.filtered_total,
        )

    def _compute_heatmap_rows(self, facts: PortfolioHeatmapFacts) -> list[PortfolioExecutiveRow]:
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
