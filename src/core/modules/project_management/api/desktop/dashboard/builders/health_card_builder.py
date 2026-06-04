"""Health card builders — schedule, cost, risk, resource and baseline variance cards."""

from __future__ import annotations
from typing import Any

from src.core.modules.project_management.api.desktop.dashboard.models.health_cards import (
    ProjectDashboardHealthCardDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.overview_builder import (
    overloaded_resource_count,
    peak_utilization_percent,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.number_formatter import (
    fmt_float,
    fmt_int,
    fmt_percent,
    fmt_ratio,
)


def build_preview_health_cards() -> tuple[ProjectDashboardHealthCardDescriptor, ...]:
    _msg = "appears when the dashboard API is connected."
    return (
        ProjectDashboardHealthCardDescriptor(id="schedule", title="Schedule Health", status_label="Preview", metric_value="SPI -", metric_label="Performance", supporting_text=f"Schedule diagnostics {_msg}", route_id="project_management.scheduling"),
        ProjectDashboardHealthCardDescriptor(id="cost", title="Cost Health", status_label="Preview", metric_value="CPI -", metric_label="Performance", supporting_text=f"Cost diagnostics {_msg}", route_id="project_management.financials"),
        ProjectDashboardHealthCardDescriptor(id="risk", title="Risk Exposure", status_label="Preview", metric_value="0", metric_label="Critical items", supporting_text=f"Risk exposure {_msg}", route_id="project_management.risk"),
        ProjectDashboardHealthCardDescriptor(id="resource", title="Resource Health", status_label="Preview", metric_value="0%", metric_label="Utilization", supporting_text=f"Resource loading {_msg}", route_id="project_management.resources"),
    )


def build_baseline_variance_card(
    project_id: str | None,
    baseline_service=None,
) -> ProjectDashboardHealthCardDescriptor:
    _no_baseline = ProjectDashboardHealthCardDescriptor(
        id="baseline_variance", title="Baseline Variance", status_label="No Baseline",
        metric_value="—", metric_label="Tasks behind plan",
        supporting_text="Approve a baseline in the Scheduling workspace to track drift.",
        meta_text="Baseline variance tracking inactive.", tone="default",
        route_id="project_management.scheduling",
    )
    if not project_id or baseline_service is None:
        return _no_baseline
    try:
        approved = baseline_service.get_approved_baseline(project_id)
    except Exception:
        approved = None
    if approved is None:
        return ProjectDashboardHealthCardDescriptor(
            id="baseline_variance", title="Baseline Variance", status_label="No Baseline",
            metric_value="—", metric_label="Tasks behind plan",
            supporting_text="No approved baseline for this project yet.",
            meta_text="Approve a baseline to enable variance tracking.", tone="default",
            route_id="project_management.scheduling",
        )
    try:
        records = tuple(baseline_service.list_variance_records(approved.id) or [])
    except Exception:
        records = ()
    behind = sum(1 for r in records if getattr(r, "finish_variance_days", 0) > 0)
    ahead = sum(1 for r in records if getattr(r, "finish_variance_days", 0) < 0)
    on_track = len(records) - behind - ahead
    tone = "danger" if behind > 0 else "success"
    return ProjectDashboardHealthCardDescriptor(
        id="baseline_variance", title="Baseline Variance",
        status_label="Behind" if behind > 0 else "On Track",
        metric_value=fmt_int(behind), metric_label="Tasks behind plan",
        supporting_text=f"Ahead: {fmt_int(ahead)} | On track: {fmt_int(on_track)} | Behind: {fmt_int(behind)}",
        meta_text=f"vs. {getattr(approved, 'name', 'approved baseline')}",
        tone=tone, route_id="project_management.scheduling",
    )


def build_health_cards(
    *,
    dashboard_data: Any,
    pending_approvals: tuple[Any, ...],
    portfolio_mode: bool,
    project_id: str | None = None,
    baseline_service=None,
) -> tuple[ProjectDashboardHealthCardDescriptor, ...]:
    kpi = getattr(dashboard_data, "kpi", None)
    evm = getattr(dashboard_data, "evm", None)
    summary = getattr(dashboard_data, "register_summary", None)
    resource_rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
    peak_util = peak_utilization_percent(resource_rows)
    overloads = overloaded_resource_count(resource_rows)

    if portfolio_mode:
        portfolio = getattr(dashboard_data, "portfolio", None)
        total_projects = int(getattr(portfolio, "projects_total", 0) or 0)
        at_risk_projects = int(getattr(portfolio, "at_risk_projects", 0) or 0)
        active_projects = int(getattr(portfolio, "active_projects", 0) or 0)
        late_tasks = int(getattr(kpi, "late_tasks", 0) or 0)
        cost_variance = float(getattr(kpi, "cost_variance", 0.0) or 0.0)
        return (
            ProjectDashboardHealthCardDescriptor(id="schedule", title="Schedule Health", status_label="At Risk" if late_tasks > 0 else "On Track", metric_value=fmt_int(late_tasks), metric_label="Late tasks", supporting_text=f"{fmt_int(active_projects)} active projects in view.", meta_text="Portfolio schedule pressure across visible work.", tone="danger" if late_tasks > 0 else "success", route_id="project_management.scheduling"),
            ProjectDashboardHealthCardDescriptor(id="cost", title="Cost Health", status_label="Attention" if cost_variance > 0.0 else "Healthy", metric_value=fmt_float(cost_variance, 0), metric_label="Cost variance", supporting_text="Portfolio actual minus planned cost.", meta_text="Positive variance indicates current overrun pressure.", tone="danger" if cost_variance > 0.0 else "success", route_id="project_management.financials"),
            ProjectDashboardHealthCardDescriptor(id="risk", title="Risk Exposure", status_label="Watch" if at_risk_projects > 0 else "Stable", metric_value=fmt_int(at_risk_projects), metric_label="Projects at risk", supporting_text=f"{fmt_int(total_projects)} total projects in scope.", meta_text="Cross-project delivery escalation load.", tone="warning" if at_risk_projects > 0 else "success", route_id="project_management.portfolio"),
            ProjectDashboardHealthCardDescriptor(id="resource", title="Resource Health", status_label="Overloaded" if overloads > 0 else "Balanced", metric_value=fmt_percent(peak_util, 0), metric_label="Peak utilization", supporting_text=f"{fmt_int(overloads)} overloaded resource(s).", meta_text=f"{fmt_int(len(pending_approvals))} pending approvals in flow.", tone="danger" if overloads > 0 else "success", route_id="project_management.resources"),
            build_baseline_variance_card(project_id, baseline_service),
        )

    late_tasks = int(getattr(kpi, "late_tasks", 0) or 0)
    critical_tasks = int(getattr(kpi, "critical_tasks", 0) or 0)
    cost_variance = float(getattr(kpi, "cost_variance", 0.0) or 0.0)
    spi = float(getattr(evm, "SPI", 1.0) or 1.0)
    cpi = float(getattr(evm, "CPI", 1.0) or 1.0)
    schedule_tone = "danger" if late_tasks > 0 or spi < 0.95 else "warning" if critical_tasks > 0 or spi < 1.0 else "success"
    cost_tone = "danger" if cost_variance > 0.0 or cpi < 0.95 else "warning" if cpi < 1.0 else "success"
    risk_critical = int(getattr(summary, "critical_items", 0) or 0)
    risk_open = int(getattr(summary, "open_risks", 0) or 0)
    risk_tone = "danger" if risk_critical > 0 else "warning" if risk_open > 0 else "success"
    resource_tone = "danger" if overloads > 0 else "warning" if peak_util >= 90.0 else "success"
    return (
        ProjectDashboardHealthCardDescriptor(id="schedule", title="Schedule Health", status_label="Late" if late_tasks > 0 else "On Track", metric_value=f"SPI {fmt_ratio(getattr(evm, 'SPI', None))}", metric_label="Schedule performance", supporting_text=f"Critical tasks {fmt_int(critical_tasks)} | Late tasks {fmt_int(late_tasks)}", meta_text="Critical-path and slip pressure across active activities.", tone=schedule_tone, route_id="project_management.scheduling"),
        ProjectDashboardHealthCardDescriptor(id="cost", title="Cost Health", status_label="Overrun" if cost_variance > 0.0 else "Stable", metric_value=f"CPI {fmt_ratio(getattr(evm, 'CPI', None))}", metric_label="Cost performance", supporting_text=f"Variance {fmt_float(cost_variance, 0)} | VAC {fmt_float(getattr(evm, 'VAC', 0.0), 0)}", meta_text="Cost and forecast pressure against the selected baseline.", tone=cost_tone, route_id="project_management.financials"),
        ProjectDashboardHealthCardDescriptor(id="risk", title="Risk Exposure", status_label="Escalated" if risk_critical > 0 else "Managed", metric_value=fmt_int(risk_critical), metric_label="Critical items", supporting_text=f"Open risks {fmt_int(risk_open)} | Pending approvals {fmt_int(len(pending_approvals))}", meta_text="Register pressure across risks, issues, and governed changes.", tone=risk_tone, route_id="project_management.risk"),
        ProjectDashboardHealthCardDescriptor(id="resource", title="Resource Health", status_label="Overloaded" if overloads > 0 else "Balanced", metric_value=fmt_percent(peak_util, 0), metric_label="Peak utilization", supporting_text=f"{fmt_int(overloads)} overloaded resource(s).", meta_text="Load pressure across assigned delivery resources.", tone=resource_tone, route_id="project_management.resources"),
        build_baseline_variance_card(project_id, baseline_service),
    )


__all__ = ["build_baseline_variance_card", "build_health_cards", "build_preview_health_cards"]
