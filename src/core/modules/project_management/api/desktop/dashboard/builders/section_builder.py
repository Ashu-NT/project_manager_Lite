"""Section builders — alerts, milestones, critical path, upcoming tasks, register, reports."""

from __future__ import annotations
from typing import Any

from src.core.modules.project_management.domain.risk.register import (
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from src.core.modules.project_management.api.desktop.dashboard.models.sections import (
    ProjectDashboardSectionDescriptor,
    ProjectDashboardSectionItemDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.number_formatter import (
    fmt_float, fmt_int, fmt_percent,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import fmt_date


def build_sections_from_dashboard_data(
    *,
    dashboard_data: Any,
    portfolio_mode: bool,
) -> tuple[ProjectDashboardSectionDescriptor, ...]:
    sections = [
        _build_alert_section(dashboard_data),
        _build_milestone_section(dashboard_data),
        _build_critical_path_section(dashboard_data),
        _build_upcoming_tasks_section(dashboard_data),
    ]
    if not portfolio_mode:
        sections.append(_build_register_urgent_section(dashboard_data))
    if portfolio_mode:
        sections.append(_build_portfolio_ranking_section(dashboard_data))
    sections.append(_build_reports_section())
    return tuple(sections)


def _build_reports_section() -> ProjectDashboardSectionDescriptor:
    common_reports = (
        ("kpi_summary", "Project KPIs", "project_management.dashboard", "Key metrics: task completion, SPI, CPI, and late count."),
        ("evm_summary", "Earned Value Summary", "project_management.financials", "BCWS, BCWP, ACWP, SPI, CPI, and VAC per period."),
        ("resource_utilization", "Resource Utilization", "project_management.resources", "Allocation %, peak load, and overload indicators per resource."),
        ("baseline_variance", "Baseline Variance", "project_management.scheduling", "Start and finish drift vs. the approved baseline per task."),
        ("risk_register", "Risk Register Summary", "project_management.register", "Open risks, issues, and change requests by severity and status."),
    )
    return ProjectDashboardSectionDescriptor(
        title="Reports",
        subtitle="Quick links to common project reports. Open the workspace to run or export each report.",
        empty_state="No reports are configured for this project.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=rid, title=title, status_label="Available", subtitle=desc, meta_text="Open workspace →", state={"routeId": route_id})
            for rid, title, route_id, desc in common_reports
        ),
    )


def _build_alert_section(dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
    alerts = tuple(getattr(dashboard_data, "alerts", []) or [])
    return ProjectDashboardSectionDescriptor(
        title="Alerts", subtitle="Current project warnings and dashboard attention items.",
        empty_state="No active alerts right now.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=f"alert-{idx}", title=str(msg), status_label="Alert", supporting_text="Generated from dashboard monitoring rules.")
            for idx, msg in enumerate(alerts, start=1)
        ),
    )


def _build_milestone_section(dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
    rows = tuple(getattr(dashboard_data, "milestone_health", []) or [])
    return ProjectDashboardSectionDescriptor(
        title="Milestones", subtitle="Key delivery checkpoints and schedule slip indicators.",
        empty_state="No milestone health rows are available yet.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=r.task_id, title=r.task_name, status_label=r.status_label, subtitle=f"Owner: {r.owner_name or 'Unassigned'}", supporting_text=f"Target: {fmt_date(r.target_date)}", meta_text="On track" if r.slip_days is None else f"Slip: {r.slip_days} day(s)", state={"slipDays": r.slip_days})
            for r in rows
        ),
    )


def _build_critical_path_section(dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
    rows = tuple(getattr(dashboard_data, "critical_watchlist", []) or [])
    return ProjectDashboardSectionDescriptor(
        title="Critical Path", subtitle="Tasks with low float or schedule pressure.",
        empty_state="No critical-path watchlist items are available yet.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=r.task_id, title=r.task_name, status_label=r.status_label, subtitle=f"Owner: {r.owner_name or 'Unassigned'}", supporting_text=f"Finish: {fmt_date(r.finish_date)} | Float: {fmt_int(r.total_float_days or 0)} day(s)", meta_text="On time" if r.late_by_days in (None, 0) else f"Late by {fmt_int(r.late_by_days)} day(s)", state={"lateByDays": r.late_by_days})
            for r in rows
        ),
    )


def _build_upcoming_tasks_section(dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
    rows = tuple(getattr(dashboard_data, "upcoming_tasks", []) or [])
    return ProjectDashboardSectionDescriptor(
        title="Upcoming Work", subtitle="Tasks that are about to start or need immediate attention.",
        empty_state="No upcoming tasks are available yet.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=r.task_id, title=r.name, status_label="Late" if r.is_late else "Critical" if r.is_critical else "Tracked", subtitle=f"Start: {fmt_date(r.start_date)} | Finish: {fmt_date(r.end_date)}", supporting_text=f"Owner: {r.main_resource or 'Unassigned'}", meta_text=f"Progress: {fmt_percent(r.percent_complete)}", state={"isLate": r.is_late, "isCritical": r.is_critical})
            for r in rows
        ),
    )


def _build_register_urgent_section(dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
    summary = getattr(dashboard_data, "register_summary", None)
    urgent_items = tuple(getattr(summary, "urgent_items", []) or []) if summary is not None else ()
    return ProjectDashboardSectionDescriptor(
        title="Urgent Register Items", subtitle="Open risks, issues, and changes that need immediate attention.",
        empty_state="No urgent register items are active right now.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=item.entry_id, title=item.title, status_label=as_register_entry_severity(item.severity).value.title(), subtitle=f"{as_register_entry_type(item.entry_type).value.title()} | Owner: {item.owner_name or 'Unassigned'}", supporting_text=f"Due: {fmt_date(item.due_date)}", meta_text=f"Status: {as_register_entry_status(item.status).value.replace('_', ' ').title()}", state={"entryType": as_register_entry_type(item.entry_type).value, "severity": as_register_entry_severity(item.severity).value, "status": as_register_entry_status(item.status).value})
            for item in urgent_items
        ),
    )


def _build_portfolio_ranking_section(dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
    rankings = tuple(getattr(getattr(dashboard_data, "portfolio", None), "project_rankings", []) or [])
    return ProjectDashboardSectionDescriptor(
        title="Portfolio Ranking", subtitle="Cross-project pressure and risk ordering from the legacy dashboard.",
        empty_state="No portfolio ranking rows are available yet.",
        items=tuple(
            ProjectDashboardSectionItemDescriptor(id=r.project_id, title=r.project_name, status_label=r.project_status, subtitle=f"Progress: {fmt_percent(r.progress_percent)} | Late: {fmt_int(r.late_tasks)} | Critical: {fmt_int(r.critical_tasks)}", supporting_text=f"Risk score: {fmt_float(r.risk_score)}", meta_text=f"Cost variance: {fmt_float(r.cost_variance)}", state={"riskScore": r.risk_score})
            for r in rankings
        ),
    )


__all__ = ["build_sections_from_dashboard_data"]
