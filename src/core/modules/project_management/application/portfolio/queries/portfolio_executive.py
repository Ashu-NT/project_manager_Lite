from __future__ import annotations

from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioRecentAction,
)
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


class PortfolioExecutiveQueryMixin:
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
                pressure = 0
                if int(kpi.late_tasks or 0) > 0:
                    pressure += 2
                if int(kpi.critical_tasks or 0) > 0:
                    pressure += 1
                if peak_utilization >= 120.0:
                    pressure += 2
                elif peak_utilization >= 100.0:
                    pressure += 1
                if float(kpi.cost_variance or 0.0) > 0:
                    pressure += 1
                rows.append(
                    PortfolioExecutiveRow(
                        project_id=project.id,
                        project_name=project.name,
                        status=getattr(project.status, "value", str(project.status)),
                        tasks_total=int(kpi.tasks_total or 0),
                        tasks_completed=int(kpi.tasks_completed or 0),
                        critical_tasks=int(kpi.critical_tasks or 0),
                        late_tasks=int(kpi.late_tasks or 0),
                        peak_resource_utilization=round(peak_utilization, 1),
                        total_planned_cost=float(kpi.total_planned_cost or 0.0),
                        total_actual_cost=float(kpi.total_actual_cost or 0.0),
                        cost_variance=float(kpi.cost_variance or 0.0),
                        pressure_score=pressure,
                        pressure_label=self._pressure_label(pressure),
                    )
                )
            except (BusinessRuleError, ValidationError, Exception):
                rows.append(
                    PortfolioExecutiveRow(
                        project_id=project.id,
                        project_name=project.name,
                        status=getattr(project.status, "value", str(project.status)),
                        tasks_total=0,
                        tasks_completed=0,
                        critical_tasks=0,
                        late_tasks=0,
                        peak_resource_utilization=0.0,
                        total_planned_cost=0.0,
                        total_actual_cost=0.0,
                        cost_variance=0.0,
                        pressure_score=0,
                        pressure_label="Stable",
                    )
                )
        return sorted(
            rows,
            key=lambda row: (-row.pressure_score, -row.late_tasks, row.project_name.lower()),
        )

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        require_permission(self._user_session, "portfolio.read", operation_label="view recent pm actions")
        _PM_PREFIXES = (
            "project.",
            "task.",
            "baseline.",
            "approval.",
            "timesheet_period.",
            "project_membership.",
            "portfolio.",
        )
        rows = []
        for row in self._audit_repo.list_recent(limit=max(limit * 4, 50)):
            action = str(getattr(row, "action", "") or "").strip().lower()
            if not any(action.startswith(prefix) for prefix in _PM_PREFIXES):
                continue
            rows.append(
                PortfolioRecentAction(
                    action=str(getattr(row, "action", "") or ""),
                    action_label=self._audit_action_label(str(getattr(row, "action", "") or "")),
                    entity_type=str(getattr(row, "entity_type", "") or ""),
                    entity_id=str(getattr(row, "entity_id", "") or ""),
                    project_id=str(getattr(row, "project_id", "") or "") or None,
                    actor_username=str(getattr(row, "actor_username", "") or ""),
                    occurred_at=getattr(row, "occurred_at", None),
                    summary=self._audit_summary(row),
                )
            )
            if len(rows) >= limit:
                break
        return rows


__all__ = ["PortfolioExecutiveQueryMixin"]
