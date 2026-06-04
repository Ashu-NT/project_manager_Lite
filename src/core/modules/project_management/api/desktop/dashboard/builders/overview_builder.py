"""Overview and headline metric builders."""

from __future__ import annotations
from typing import Any

from src.core.modules.project_management.api.desktop.dashboard.models.overview import (
    ProjectDashboardMetricDescriptor,
    ProjectDashboardOverviewDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.number_formatter import (
    fmt_float,
    fmt_int,
    fmt_percent,
    fmt_ratio,
)

_PORTFOLIO_SUBTITLES = {
    "executive": "Executive portfolio command center",
    "pmo": "PMO portfolio operations and escalation view",
    "project_manager": "Cross-project delivery control view",
    "resource_manager": "Cross-project resource pressure view",
    "financial": "Portfolio financial control view",
}

_PROJECT_SUBTITLES = {
    "executive": "Executive project command center",
    "pmo": "PMO project health and escalation view",
    "project_manager": "Project manager delivery-control view",
    "resource_manager": "Resource loading and capacity control view",
    "financial": "Project financial control view",
}

_PORTFOLIO_METRIC_ORDER = {
    "executive": ("total_projects", "active_projects", "on_track", "delayed", "budget_variance", "high_risks", "open_tasks", "utilization"),
    "pmo": ("active_projects", "on_track", "delayed", "critical_tasks", "high_risks", "pending_approvals", "open_tasks", "utilization"),
    "project_manager": ("active_projects", "delayed", "critical_tasks", "high_risks", "open_tasks", "pending_approvals", "utilization", "budget_variance"),
    "resource_manager": ("active_projects", "utilization", "open_tasks", "delayed", "critical_tasks", "high_risks", "pending_approvals", "budget_variance"),
    "financial": ("budget_variance", "pending_approvals", "active_projects", "delayed", "open_tasks", "high_risks", "utilization", "total_projects"),
}

_PROJECT_METRIC_ORDER = {
    "executive": ("progress", "spi", "cpi", "budget_variance", "forecast_variance", "high_risks", "open_tasks", "utilization"),
    "pmo": ("progress", "delayed", "critical_tasks", "high_risks", "pending_approvals", "open_tasks", "spi", "cpi"),
    "project_manager": ("progress", "delayed", "critical_tasks", "open_tasks", "high_risks", "pending_approvals", "utilization", "spi"),
    "resource_manager": ("utilization", "open_tasks", "delayed", "critical_tasks", "progress", "pending_approvals", "high_risks", "budget_variance"),
    "financial": ("budget_variance", "forecast_variance", "cpi", "spi", "pending_approvals", "high_risks", "open_tasks", "progress"),
}


def average_utilization_percent(rows: tuple[Any, ...]) -> float:
    if not rows:
        return 0.0
    values = [
        float(getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0)
        for r in rows
    ]
    return sum(values) / max(len(values), 1)


def peak_utilization_percent(rows: tuple[Any, ...]) -> float:
    if not rows:
        return 0.0
    return max(
        float(getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0)
        for r in rows
    )


def overloaded_resource_count(rows: tuple[Any, ...]) -> int:
    return sum(
        1 for r in rows
        if float(getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0) > 100.0
    )


def build_empty_overview() -> ProjectDashboardOverviewDescriptor:
    return ProjectDashboardOverviewDescriptor(
        title="Dashboard",
        subtitle="Select a project to see schedule and cost health.",
        metrics=(
            ProjectDashboardMetricDescriptor("Tasks", "0 / 0", "Done / Total"),
            ProjectDashboardMetricDescriptor("Progress", "0.00%", "Completion"),
            ProjectDashboardMetricDescriptor("In flight", "0", "Active work"),
            ProjectDashboardMetricDescriptor("Blocked", "0", "Needs action"),
            ProjectDashboardMetricDescriptor("Critical", "0", "Path pressure"),
            ProjectDashboardMetricDescriptor("Late", "0", "Behind plan"),
            ProjectDashboardMetricDescriptor("Cost variance", "0.00", "Actual - Planned"),
            ProjectDashboardMetricDescriptor("Spend vs plan", "0 / 0", "Actual / planned"),
        ),
    )


def build_overview_from_dashboard_data(
    *,
    project_name: str,
    dashboard_data: Any,
) -> ProjectDashboardOverviewDescriptor:
    kpi = dashboard_data.kpi
    tasks_total = int(getattr(kpi, "tasks_total", 0) or 0)
    tasks_completed = int(getattr(kpi, "tasks_completed", 0) or 0)
    progress = 100.0 * tasks_completed / tasks_total if tasks_total else 0.0
    title = project_name or getattr(kpi, "name", "") or "Dashboard"
    return ProjectDashboardOverviewDescriptor(
        title=title,
        subtitle="Project execution health",
        metrics=(
            ProjectDashboardMetricDescriptor("Tasks", f"{fmt_int(tasks_completed)} / {fmt_int(tasks_total)}", "Done / Total"),
            ProjectDashboardMetricDescriptor("Progress", fmt_percent(progress), "Completion"),
            ProjectDashboardMetricDescriptor("In flight", fmt_int(getattr(kpi, "tasks_in_progress", 0)), "Active work"),
            ProjectDashboardMetricDescriptor("Blocked", fmt_int(getattr(kpi, "task_blocked", 0)), "Needs action"),
            ProjectDashboardMetricDescriptor("Critical", fmt_int(getattr(kpi, "critical_tasks", 0)), "Path pressure"),
            ProjectDashboardMetricDescriptor("Late", fmt_int(getattr(kpi, "late_tasks", 0)), "Behind plan"),
            ProjectDashboardMetricDescriptor("Cost variance", fmt_float(getattr(kpi, "cost_variance", 0.0)), "Actual - Planned"),
            ProjectDashboardMetricDescriptor(
                "Spend vs plan",
                f"{fmt_float(getattr(kpi, 'total_actual_cost', 0.0), 0)} / {fmt_float(getattr(kpi, 'total_planned_cost', 0.0), 0)}",
                "Actual / planned",
            ),
        ),
    )


def build_contextual_overview(
    *,
    project_name: str,
    dashboard_data: Any,
    pending_approval_count: int,
    selected_view_key: str,
    portfolio_mode: bool,
) -> ProjectDashboardOverviewDescriptor:
    kpi = getattr(dashboard_data, "kpi", None)
    title = project_name or getattr(kpi, "name", "") or "Dashboard"

    if portfolio_mode:
        return _build_portfolio_overview(title=title, dashboard_data=dashboard_data, kpi=kpi, pending_approval_count=pending_approval_count, selected_view_key=selected_view_key)
    return _build_project_overview(title=title, dashboard_data=dashboard_data, kpi=kpi, pending_approval_count=pending_approval_count, selected_view_key=selected_view_key)


def _build_portfolio_overview(
    *,
    title: str,
    dashboard_data: Any,
    kpi: Any,
    pending_approval_count: int,
    selected_view_key: str,
) -> ProjectDashboardOverviewDescriptor:
    portfolio = getattr(dashboard_data, "portfolio", None)
    total_projects = int(getattr(portfolio, "projects_total", 0) or 0)
    active_projects = int(getattr(portfolio, "active_projects", 0) or 0)
    at_risk_projects = int(getattr(portfolio, "at_risk_projects", 0) or 0)
    on_hold_projects = int(getattr(portfolio, "on_hold_projects", 0) or 0)
    on_track_projects = max(total_projects - at_risk_projects - on_hold_projects, 0)
    open_tasks = max(int(getattr(kpi, "tasks_total", 0) or 0) - int(getattr(kpi, "tasks_completed", 0) or 0), 0)
    resource_rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
    utilization = average_utilization_percent(resource_rows)

    metrics_by_id = {
        "total_projects": ProjectDashboardMetricDescriptor("Total Projects", fmt_int(total_projects), "Portfolio footprint"),
        "active_projects": ProjectDashboardMetricDescriptor("Active", fmt_int(active_projects), "Projects currently executing"),
        "on_track": ProjectDashboardMetricDescriptor("On Track", fmt_int(on_track_projects), "Projects without current risk flags"),
        "delayed": ProjectDashboardMetricDescriptor("Delayed", fmt_int(getattr(kpi, "late_tasks", 0)), "Late tasks across visible projects"),
        "budget_variance": ProjectDashboardMetricDescriptor("Budget Var.", fmt_float(getattr(kpi, "cost_variance", 0.0), 0), "Portfolio actual minus planned"),
        "high_risks": ProjectDashboardMetricDescriptor("At Risk", fmt_int(at_risk_projects), "Projects requiring intervention"),
        "open_tasks": ProjectDashboardMetricDescriptor("Open Tasks", fmt_int(open_tasks), "Tasks not yet complete"),
        "utilization": ProjectDashboardMetricDescriptor("Utilization", fmt_percent(utilization, 0), "Average visible resource load"),
        "pending_approvals": ProjectDashboardMetricDescriptor("Approvals", fmt_int(pending_approval_count), "Pending governed changes"),
        "critical_tasks": ProjectDashboardMetricDescriptor("Critical", fmt_int(getattr(kpi, "critical_tasks", 0)), "Critical tasks across visible projects"),
    }
    subtitle = _PORTFOLIO_SUBTITLES.get(selected_view_key, "Executive portfolio command center")
    order = _PORTFOLIO_METRIC_ORDER.get(selected_view_key, ())
    return ProjectDashboardOverviewDescriptor(
        title=title, subtitle=subtitle,
        metrics=tuple(metrics_by_id[k] for k in order if k in metrics_by_id),
    )


def _build_project_overview(
    *,
    title: str,
    dashboard_data: Any,
    kpi: Any,
    pending_approval_count: int,
    selected_view_key: str,
) -> ProjectDashboardOverviewDescriptor:
    evm = getattr(dashboard_data, "evm", None)
    summary = getattr(dashboard_data, "register_summary", None)
    tasks_total = int(getattr(kpi, "tasks_total", 0) or 0)
    tasks_completed = int(getattr(kpi, "tasks_completed", 0) or 0)
    open_tasks = max(tasks_total - tasks_completed, 0)
    progress = 100.0 * tasks_completed / tasks_total if tasks_total else 0.0
    resource_rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
    utilization = average_utilization_percent(resource_rows)
    overloads = overloaded_resource_count(resource_rows)

    metrics_by_id = {
        "progress": ProjectDashboardMetricDescriptor("Progress", fmt_percent(progress, 0), "Project completion"),
        "spi": ProjectDashboardMetricDescriptor("SPI", fmt_ratio(getattr(evm, "SPI", None)), "Schedule performance index"),
        "cpi": ProjectDashboardMetricDescriptor("CPI", fmt_ratio(getattr(evm, "CPI", None)), "Cost performance index"),
        "budget_variance": ProjectDashboardMetricDescriptor("Budget Var.", fmt_float(getattr(kpi, "cost_variance", 0.0), 0), "Actual minus planned cost"),
        "forecast_variance": ProjectDashboardMetricDescriptor("Forecast Var.", fmt_float(getattr(evm, "VAC", 0.0), 0), "Variance at completion"),
        "high_risks": ProjectDashboardMetricDescriptor("High Risks", fmt_int(getattr(summary, "critical_items", 0) or 0), "Critical register exposure"),
        "open_tasks": ProjectDashboardMetricDescriptor("Open Tasks", fmt_int(open_tasks), "Tasks not yet complete"),
        "pending_approvals": ProjectDashboardMetricDescriptor("Approvals", fmt_int(pending_approval_count), "Pending governed changes"),
        "utilization": ProjectDashboardMetricDescriptor(
            "Utilization", fmt_percent(utilization, 0),
            f"{fmt_int(overloads)} overloaded resource(s)" if overloads else "Resource load within capacity",
        ),
        "delayed": ProjectDashboardMetricDescriptor("Delayed", fmt_int(getattr(kpi, "late_tasks", 0)), "Tasks behind target dates"),
        "critical_tasks": ProjectDashboardMetricDescriptor("Critical", fmt_int(getattr(kpi, "critical_tasks", 0)), "Critical-path tasks"),
    }
    subtitle = _PROJECT_SUBTITLES.get(selected_view_key, "Executive project command center")
    order = _PROJECT_METRIC_ORDER.get(selected_view_key, ())
    return ProjectDashboardOverviewDescriptor(
        title=title, subtitle=subtitle,
        metrics=tuple(metrics_by_id[k] for k in order if k in metrics_by_id),
    )


__all__ = [
    "average_utilization_percent",
    "build_contextual_overview",
    "build_empty_overview",
    "build_overview_from_dashboard_data",
    "overloaded_resource_count",
    "peak_utilization_percent",
]
