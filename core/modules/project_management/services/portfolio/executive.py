from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioRecentAction,
)
from src.core.platform.auth.authorization import require_permission


class PortfolioExecutiveMixin:
    def list_portfolio_heatmap(self) -> list[PortfolioExecutiveRow]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio executive heatmap")
        rows: list[PortfolioExecutiveRow] = []
        for project in self._accessible_projects():
            try:
                kpi = self._reporting.get_project_kpis(project.id)
                resource_rows = self._reporting.get_resource_load_summary(project.id)
                peak_utilization = max(
                    (
                        float(getattr(row, "utilization_percent", 0.0) or 0.0)
                        for row in resource_rows
                    ),
                    default=0.0,
                )
                pressure_score = 0
                if int(kpi.late_tasks or 0) > 0:
                    pressure_score += 2
                if int(kpi.critical_tasks or 0) > 0:
                    pressure_score += 1
                if peak_utilization > 100.0:
                    pressure_score += 2
                elif peak_utilization >= 85.0:
                    pressure_score += 1
                if float(kpi.cost_variance or 0.0) > 0.0:
                    pressure_score += 1
                pressure_label = self._pressure_label(pressure_score)
                late_tasks = int(kpi.late_tasks or 0)
                critical_tasks = int(kpi.critical_tasks or 0)
                cost_variance = float(kpi.cost_variance or 0.0)
            except (BusinessRuleError, ValidationError):
                peak_utilization = 0.0
                pressure_score = 0
                pressure_label = "Needs Schedule"
                late_tasks = 0
                critical_tasks = 0
                cost_variance = 0.0
            rows.append(
                PortfolioExecutiveRow(
                    project_id=project.id,
                    project_name=project.name,
                    project_status=getattr(project.status, "value", str(project.status)),
                    late_tasks=late_tasks,
                    critical_tasks=critical_tasks,
                    peak_utilization_percent=peak_utilization,
                    cost_variance=cost_variance,
                    pressure_score=pressure_score,
                    pressure_label=pressure_label,
                )
            )
        return sorted(
            rows,
            key=lambda row: (
                -row.pressure_score,
                -row.late_tasks,
                -row.peak_utilization_percent,
                row.project_name.lower(),
            ),
        )

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        require_permission(self._user_session, "portfolio.read", operation_label="view recent PM actions")
        accessible_projects = {project.id: project.name for project in self._accessible_projects()}
        pm_prefixes = (
            "project.",
            "task.",
            "baseline.",
            "approval.",
            "timesheet_period.",
            "project_membership.",
            "portfolio.",
        )
        recent_rows = self._audit_repo.list_recent(limit=max(limit * 8, 120))
        actions: list[PortfolioRecentAction] = []
        for row in recent_rows:
            if row.project_id and row.project_id not in accessible_projects:
                continue
            if not str(row.action or "").startswith(pm_prefixes):
                continue
            actions.append(
                PortfolioRecentAction(
                    occurred_at=row.occurred_at,
                    project_name=accessible_projects.get(row.project_id or "", "Platform / Shared"),
                    actor_username=row.actor_username or "system",
                    action_label=self._audit_action_label(row.action),
                    summary=self._audit_summary(row),
                )
            )
            if len(actions) >= limit:
                break
        return actions


__all__ = ["PortfolioExecutiveMixin"]
