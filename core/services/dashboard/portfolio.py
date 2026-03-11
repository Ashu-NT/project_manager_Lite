from __future__ import annotations

from datetime import date

from core.domain.enums import ProjectStatus
from core.services.dashboard.models import DashboardData
from core.services.dashboard.portfolio_models import (
    PORTFOLIO_SCOPE_ID,
    DashboardPortfolio,
    PortfolioProjectRow,
    PortfolioStatusRollupRow,
)
from core.services.reporting.models import ProjectKPI, ResourceLoadRow


class DashboardPortfolioMixin:
    def get_portfolio_data(self) -> DashboardData:
        projects = self._projects.list_projects()
        if not projects:
            return DashboardData(
                kpi=self._build_portfolio_kpi(),
                alerts=["Portfolio has no projects yet."],
                resource_load=[],
                burndown=[],
                cost_sources=None,
                evm=None,
                upcoming_tasks=[],
                portfolio=DashboardPortfolio(
                    projects_total=0,
                    active_projects=0,
                    completed_projects=0,
                    on_hold_projects=0,
                    at_risk_projects=0,
                    status_rollup=[],
                    project_rankings=[],
                ),
            )

        task_totals = {
            "tasks_total": 0,
            "tasks_completed": 0,
            "tasks_in_progress": 0,
            "task_blocked": 0,
            "tasks_not_started": 0,
            "critical_tasks": 0,
            "late_tasks": 0,
        }
        cost_totals = {
            "total_planned_cost": 0.0,
            "total_actual_cost": 0.0,
            "total_committed_cost": 0.0,
            "cost_variance": 0.0,
            "committment_variance": 0.0,
        }
        earliest_start: date | None = None
        latest_end: date | None = None
        active_projects = 0
        completed_projects = 0
        on_hold_projects = 0
        at_risk_projects = 0
        status_counts: dict[str, int] = {}
        ranking_rows: list[PortfolioProjectRow] = []
        upcoming_rows = []
        resource_load_by_id: dict[str, ResourceLoadRow] = {}

        for project in projects:
            kpi = self._reporting.get_project_kpis(project.id)
            for key in task_totals:
                task_totals[key] += int(getattr(kpi, key, 0) or 0)
            for key in cost_totals:
                cost_totals[key] += float(getattr(kpi, key, 0.0) or 0.0)

            if kpi.start_date is not None:
                earliest_start = kpi.start_date if earliest_start is None else min(earliest_start, kpi.start_date)
            if kpi.end_date is not None:
                latest_end = kpi.end_date if latest_end is None else max(latest_end, kpi.end_date)

            status_value = getattr(getattr(project, "status", None), "value", getattr(project, "status", "PLANNED"))
            status_value = str(status_value or "PLANNED").upper()
            status_counts[status_value] = status_counts.get(status_value, 0) + 1
            if status_value == ProjectStatus.ACTIVE.value:
                active_projects += 1
            elif status_value == ProjectStatus.COMPLETED.value:
                completed_projects += 1
            elif status_value == ProjectStatus.ON_HOLD.value:
                on_hold_projects += 1

            risk_score = self._portfolio_risk_score(status_value=status_value, kpi=kpi)
            if self._portfolio_is_at_risk(status_value=status_value, kpi=kpi):
                at_risk_projects += 1

            progress_percent = 0.0
            if kpi.tasks_total > 0:
                progress_percent = (float(kpi.tasks_completed) / float(kpi.tasks_total)) * 100.0
            ranking_rows.append(
                PortfolioProjectRow(
                    project_id=project.id,
                    project_name=project.name,
                    project_status=status_value,
                    progress_percent=progress_percent,
                    late_tasks=int(kpi.late_tasks or 0),
                    critical_tasks=int(kpi.critical_tasks or 0),
                    cost_variance=float(kpi.cost_variance or 0.0),
                    risk_score=risk_score,
                )
            )

            for upcoming in self._build_upcoming_tasks(project.id):
                upcoming.name = f"{project.name} | {upcoming.name}"
                upcoming_rows.append(upcoming)

            for row in self._reporting.get_resource_load_summary(project.id):
                existing = resource_load_by_id.get(row.resource_id)
                if existing is None:
                    resource_load_by_id[row.resource_id] = ResourceLoadRow(
                        resource_id=row.resource_id,
                        resource_name=row.resource_name,
                        total_allocation_percent=float(row.total_allocation_percent or 0.0),
                        tasks_count=int(row.tasks_count or 0),
                        capacity_percent=float(row.capacity_percent or 100.0),
                        utilization_percent=float(row.utilization_percent or 0.0),
                    )
                    continue
                existing.total_allocation_percent += float(row.total_allocation_percent or 0.0)
                existing.tasks_count += int(row.tasks_count or 0)
                existing.capacity_percent = max(
                    float(existing.capacity_percent or 100.0),
                    float(row.capacity_percent or 100.0),
                )
                capacity = float(existing.capacity_percent or 100.0) or 100.0
                existing.utilization_percent = (float(existing.total_allocation_percent or 0.0) / capacity) * 100.0

        ranking_rows.sort(
            key=lambda row: (
                row.risk_score,
                row.late_tasks,
                row.critical_tasks,
                row.cost_variance,
            ),
            reverse=True,
        )
        upcoming_rows.sort(key=lambda row: (row.start_date or date.max, row.name))
        resource_load = sorted(
            resource_load_by_id.values(),
            key=lambda row: float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0),
            reverse=True,
        )
        status_rollup = self._build_status_rollup(status_counts)
        portfolio = DashboardPortfolio(
            projects_total=len(projects),
            active_projects=active_projects,
            completed_projects=completed_projects,
            on_hold_projects=on_hold_projects,
            at_risk_projects=at_risk_projects,
            status_rollup=status_rollup,
            project_rankings=ranking_rows,
        )
        return DashboardData(
            kpi=self._build_portfolio_kpi(
                start_date=earliest_start,
                end_date=latest_end,
                **task_totals,
                **cost_totals,
            ),
            alerts=self._build_portfolio_alerts(portfolio=portfolio, resource_load=resource_load, cost_variance=cost_totals["cost_variance"]),
            resource_load=resource_load,
            burndown=[],
            cost_sources=None,
            evm=None,
            upcoming_tasks=upcoming_rows[:20],
            portfolio=portfolio,
        )

    def _build_portfolio_kpi(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        tasks_total: int = 0,
        tasks_completed: int = 0,
        tasks_in_progress: int = 0,
        task_blocked: int = 0,
        tasks_not_started: int = 0,
        critical_tasks: int = 0,
        late_tasks: int = 0,
        total_planned_cost: float = 0.0,
        total_actual_cost: float = 0.0,
        total_committed_cost: float = 0.0,
        cost_variance: float = 0.0,
        committment_variance: float = 0.0,
    ) -> ProjectKPI:
        duration_working_days = None
        if start_date is not None and end_date is not None:
            duration_working_days = self._calendar.working_days_between(start_date, end_date)
        return ProjectKPI(
            project_id=PORTFOLIO_SCOPE_ID,
            name="Portfolio Overview",
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
            total_planned_cost=total_planned_cost,
            total_actual_cost=total_actual_cost,
            cost_variance=cost_variance,
            total_committed_cost=total_committed_cost,
            committment_variance=committment_variance,
        )

    @staticmethod
    def _portfolio_risk_score(*, status_value: str, kpi: ProjectKPI) -> float:
        score = 0.0
        if status_value == ProjectStatus.ON_HOLD.value:
            score += 25.0
        score += float(kpi.late_tasks or 0) * 12.0
        score += float(kpi.critical_tasks or 0) * 4.0
        if float(kpi.total_planned_cost or 0.0) > 0.0 and float(kpi.cost_variance or 0.0) > 0.0:
            score += (float(kpi.cost_variance or 0.0) / float(kpi.total_planned_cost or 1.0)) * 20.0
        elif float(kpi.cost_variance or 0.0) > 0.0:
            score += 8.0
        return score

    @staticmethod
    def _portfolio_is_at_risk(*, status_value: str, kpi: ProjectKPI) -> bool:
        return (
            status_value == ProjectStatus.ON_HOLD.value
            or int(kpi.late_tasks or 0) > 0
            or int(kpi.critical_tasks or 0) > 0
            or float(kpi.cost_variance or 0.0) > 0.0
        )

    @staticmethod
    def _build_status_rollup(status_counts: dict[str, int]) -> list[PortfolioStatusRollupRow]:
        ordered = [
            ProjectStatus.ACTIVE.value,
            ProjectStatus.ON_HOLD.value,
            ProjectStatus.PLANNED.value,
            ProjectStatus.COMPLETED.value,
        ]
        rows = [PortfolioStatusRollupRow(status_label=status, project_count=int(status_counts.get(status, 0) or 0)) for status in ordered]
        for status, count in sorted(status_counts.items()):
            if status in ordered:
                continue
            rows.append(PortfolioStatusRollupRow(status_label=status, project_count=int(count or 0)))
        return rows

    @staticmethod
    def _build_portfolio_alerts(
        *,
        portfolio: DashboardPortfolio,
        resource_load: list[ResourceLoadRow],
        cost_variance: float,
    ) -> list[str]:
        alerts: list[str] = []
        if portfolio.projects_total == 0:
            return ["Portfolio has no projects yet."]
        if portfolio.at_risk_projects > 0:
            alerts.append(f"{portfolio.at_risk_projects} project(s) are at risk across the portfolio.")
        if portfolio.on_hold_projects > 0:
            alerts.append(f"{portfolio.on_hold_projects} project(s) are currently on hold.")
        overloaded = [
            row
            for row in resource_load
            if float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0) > 100.0
        ]
        if overloaded:
            alerts.append(f"{len(overloaded)} resource(s) exceed capacity across the portfolio.")
        if float(cost_variance or 0.0) > 0.0:
            alerts.append(f"Portfolio actual cost exceeds plan by {float(cost_variance):.2f}.")
        if portfolio.project_rankings and portfolio.project_rankings[0].risk_score > 0.0:
            top = portfolio.project_rankings[0]
            alerts.append(
                f'Highest-risk project is "{top.project_name}" '
                f"({top.late_tasks} late task(s), {top.critical_tasks} critical task(s))."
            )
        return alerts


__all__ = ["DashboardPortfolioMixin"]
