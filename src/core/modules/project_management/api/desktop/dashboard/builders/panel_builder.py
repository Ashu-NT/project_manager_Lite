"""Panel builders — EVM, register, cost sources, baseline variance, resources, reports."""

from __future__ import annotations
from typing import Any

from src.core.modules.project_management.api.desktop.dashboard.models.overview import ProjectDashboardMetricDescriptor
from src.core.modules.project_management.api.desktop.dashboard.models.panels import (
    ProjectDashboardPanelDescriptor,
    ProjectDashboardPanelRowDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.number_formatter import (
    fmt_float, fmt_int, fmt_percent, fmt_ratio,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.date_formatter import fmt_date

_PREVIEW_MSG = "Project-management dashboard desktop API is not connected in this QML preview."


def build_preview_panels() -> tuple[ProjectDashboardPanelDescriptor, ...]:
    return (
        ProjectDashboardPanelDescriptor(title="Earned Value (EVM)", subtitle="Schedule and cost performance against the selected baseline.", empty_state=_PREVIEW_MSG),
        ProjectDashboardPanelDescriptor(title="Register Summary", subtitle="Risk, issue, and change pressure for the selected project.", empty_state=_PREVIEW_MSG),
        ProjectDashboardPanelDescriptor(title="Cost Sources", subtitle="Planned, committed, and actual cost-source visibility.", empty_state=_PREVIEW_MSG),
        ProjectDashboardPanelDescriptor(title="Baseline Variance", subtitle="Task schedule and cost drift between baselines.", empty_state=_PREVIEW_MSG),
        ProjectDashboardPanelDescriptor(title="Resource Overloads", subtitle="Resources that exceed capacity across assigned activities.", empty_state=_PREVIEW_MSG),
        ProjectDashboardPanelDescriptor(title="Available Reports", subtitle="Report formats available for this project.", empty_state=_PREVIEW_MSG),
    )


def build_panels_from_dashboard_data(
    *,
    dashboard_data: Any,
    baseline_label: str,
    selected_baseline_id: str,
    portfolio_mode: bool,
    baseline_service=None,
) -> tuple[ProjectDashboardPanelDescriptor, ...]:
    return (
        _build_evm_panel(dashboard_data=dashboard_data, baseline_label=baseline_label, portfolio_mode=portfolio_mode),
        _build_register_panel(dashboard_data=dashboard_data, portfolio_mode=portfolio_mode),
        _build_cost_sources_panel(dashboard_data=dashboard_data, portfolio_mode=portfolio_mode),
        _build_baseline_variance_panel(selected_baseline_id=selected_baseline_id, portfolio_mode=portfolio_mode, baseline_service=baseline_service),
        _build_resource_overload_panel(dashboard_data=dashboard_data, portfolio_mode=portfolio_mode),
        _build_reports_panel(portfolio_mode=portfolio_mode),
    )


def _build_panel_row(label: str, text: str) -> ProjectDashboardPanelRowDescriptor:
    normalized = " ".join(str(text or "-").split())
    lowered = normalized.lower()
    tone = "default"
    if any(t in lowered for t in ("late", "over budget", "unfavorable", "above target")):
        tone = "danger"
    elif any(t in lowered for t in ("watch", "monitor", "attention", "recover")):
        tone = "warning"
    elif any(t in lowered for t in ("favorable", "ahead", "healthy", "within target")):
        tone = "success"
    return ProjectDashboardPanelRowDescriptor(label=label, value=normalized or "-", tone=tone)


def _build_evm_panel(*, dashboard_data: Any, baseline_label: str, portfolio_mode: bool) -> ProjectDashboardPanelDescriptor:
    if portfolio_mode:
        return ProjectDashboardPanelDescriptor(title="Earned Value (EVM)", subtitle="Schedule and cost performance against the selected baseline.", empty_state="EVM remains project-scoped and is not rolled up in portfolio mode.")
    evm = getattr(dashboard_data, "evm", None)
    if evm is None:
        return ProjectDashboardPanelDescriptor(title="Earned Value (EVM)", subtitle="Schedule and cost performance against the selected baseline.", empty_state="Create a baseline to enable EVM metrics for this dashboard.")
    status_parts = [p.strip() for p in str(getattr(evm, "status_text", "") or "").split(".") if p.strip()]
    return ProjectDashboardPanelDescriptor(
        title="Earned Value (EVM)", subtitle="Schedule and cost performance against the selected baseline.",
        hint=f"As of {fmt_date(evm.as_of)} (baseline: {baseline_label})",
        rows=(
            _build_panel_row("Cost", status_parts[0] if len(status_parts) > 0 else "-"),
            _build_panel_row("Schedule", status_parts[1] if len(status_parts) > 1 else "-"),
            _build_panel_row("Forecast", status_parts[2] if len(status_parts) > 2 else "-"),
            _build_panel_row("TCPI", status_parts[3] if len(status_parts) > 3 else "-"),
        ),
        metrics=(
            ProjectDashboardMetricDescriptor("CPI", fmt_ratio(evm.CPI), "Cost performance"),
            ProjectDashboardMetricDescriptor("SPI", fmt_ratio(evm.SPI), "Schedule performance"),
            ProjectDashboardMetricDescriptor("PV", fmt_float(evm.PV), "Planned value"),
            ProjectDashboardMetricDescriptor("EV", fmt_float(evm.EV), "Earned value"),
            ProjectDashboardMetricDescriptor("AC", fmt_float(evm.AC), "Actual cost"),
            ProjectDashboardMetricDescriptor("EAC", fmt_float(evm.EAC), "Estimate at completion"),
            ProjectDashboardMetricDescriptor("VAC", fmt_float(evm.VAC), "Variance at completion"),
            ProjectDashboardMetricDescriptor("TCPI(BAC)", fmt_ratio(evm.TCPI_to_BAC), "Needed to hit BAC"),
            ProjectDashboardMetricDescriptor("TCPI(EAC)", fmt_ratio(evm.TCPI_to_EAC), "Needed to hit EAC"),
        ),
    )


def _build_register_panel(*, dashboard_data: Any, portfolio_mode: bool) -> ProjectDashboardPanelDescriptor:
    if portfolio_mode:
        return ProjectDashboardPanelDescriptor(title="Register Summary", subtitle="Risk, issue, and change pressure for the selected project.", empty_state="Register rollups remain project-scoped and are not summarized in portfolio mode.")
    summary = getattr(dashboard_data, "register_summary", None)
    if summary is None:
        return ProjectDashboardPanelDescriptor(title="Register Summary", subtitle="Risk, issue, and change pressure for the selected project.", empty_state="No register summary is available yet for this project.")
    return ProjectDashboardPanelDescriptor(
        title="Register Summary", subtitle="Risk, issue, and change pressure for the selected project.",
        rows=(
            ProjectDashboardPanelRowDescriptor("Open risks", fmt_int(summary.open_risks), "Open register risks"),
            ProjectDashboardPanelRowDescriptor("Open issues", fmt_int(summary.open_issues), "Open execution issues"),
            ProjectDashboardPanelRowDescriptor("Pending changes", fmt_int(summary.pending_changes), "Changes awaiting closure"),
            ProjectDashboardPanelRowDescriptor("Overdue items", fmt_int(summary.overdue_items), "Past due register entries", tone="danger" if int(summary.overdue_items or 0) > 0 else "default"),
            ProjectDashboardPanelRowDescriptor("Critical items", fmt_int(summary.critical_items), "Critical-severity register entries", tone="danger" if int(summary.critical_items or 0) > 0 else "default"),
        ),
    )


def _build_cost_sources_panel(*, dashboard_data: Any, portfolio_mode: bool) -> ProjectDashboardPanelDescriptor:
    if portfolio_mode:
        return ProjectDashboardPanelDescriptor(title="Cost Sources", subtitle="Planned, committed, and actual cost-source visibility.", empty_state="Cost-source breakdown remains project-scoped and is not summarized in portfolio mode.")
    sources = getattr(dashboard_data, "cost_sources", None)
    rows = tuple(getattr(sources, "rows", []) or []) if sources is not None else ()
    if not rows:
        return ProjectDashboardPanelDescriptor(title="Cost Sources", subtitle="Planned, committed, and actual cost-source visibility.", empty_state="No cost-source breakdown is available yet for this project.")
    return ProjectDashboardPanelDescriptor(
        title="Cost Sources", subtitle="Planned, committed, and actual cost-source visibility.",
        rows=tuple(ProjectDashboardPanelRowDescriptor(label=r.source_label, value=f"{fmt_float(r.actual, 0)} / {fmt_float(r.planned, 0)}", supporting_text=f"Committed: {fmt_float(r.committed, 0)}", tone="warning" if float(r.actual or 0.0) > float(r.planned or 0.0) else "default") for r in rows),
    )


def _build_baseline_variance_panel(*, selected_baseline_id: str, portfolio_mode: bool, baseline_service=None) -> ProjectDashboardPanelDescriptor:
    if portfolio_mode:
        return ProjectDashboardPanelDescriptor(title="Baseline Variance", subtitle="Task schedule and cost drift between baselines.", empty_state="Baseline variance records are project-scoped and not rolled up in portfolio mode.")
    if not selected_baseline_id or baseline_service is None:
        return ProjectDashboardPanelDescriptor(title="Baseline Variance", subtitle="Task schedule and cost drift between baselines.", empty_state="Select a baseline to view schedule and cost variance records.")
    try:
        records = baseline_service.list_variance_records(selected_baseline_id)
    except Exception:
        records = []
    if not records:
        return ProjectDashboardPanelDescriptor(title="Baseline Variance", subtitle="Task schedule and cost drift between baselines.", empty_state="No variance records found for the selected baseline.")
    sorted_records = sorted(records, key=lambda r: abs(r.start_variance_days or 0) + abs(r.finish_variance_days or 0), reverse=True)[:8]
    return ProjectDashboardPanelDescriptor(
        title="Baseline Variance", subtitle=f"Top {len(sorted_records)} task(s) with schedule or cost drift.",
        rows=tuple(
            ProjectDashboardPanelRowDescriptor(
                label=str(r.task_name or r.task_id or "Task"),
                value=f"{r.start_variance_days:+d}d / {r.finish_variance_days:+d}d",
                supporting_text=f"Cost delta: {fmt_float(r.cost_variance, 0)}" if r.cost_variance != 0.0 else "No cost drift",
                tone="danger" if abs(r.finish_variance_days or 0) > 5 else "warning" if abs(r.finish_variance_days or 0) > 0 else "default",
            )
            for r in sorted_records
        ),
    )


def _build_resource_overload_panel(*, dashboard_data: Any, portfolio_mode: bool) -> ProjectDashboardPanelDescriptor:
    rows = tuple(getattr(dashboard_data, "resource_load", []) or [])

    def _util(r):
        return float(getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0)

    overloaded = [r for r in rows if _util(r) > 100.0]
    at_risk = [r for r in rows if 90.0 <= _util(r) <= 100.0]
    if not rows:
        return ProjectDashboardPanelDescriptor(title="Resource Overloads", subtitle="Resources that exceed capacity across assigned activities.", empty_state="No resource loading data is available yet.")
    if not overloaded and not at_risk:
        return ProjectDashboardPanelDescriptor(
            title="Resource Overloads", subtitle="All resources are within capacity.",
            metrics=(ProjectDashboardMetricDescriptor("Resources", fmt_int(len(rows)), "In scope"), ProjectDashboardMetricDescriptor("Overloaded", "0", "Above 100% capacity"), ProjectDashboardMetricDescriptor("At Risk", "0", "90–100% utilization")),
        )
    display = (overloaded + at_risk)[:8]
    return ProjectDashboardPanelDescriptor(
        title="Resource Overloads", subtitle=f"{fmt_int(len(overloaded))} overloaded, {fmt_int(len(at_risk))} near-capacity.",
        metrics=(ProjectDashboardMetricDescriptor("Resources", fmt_int(len(rows)), "In scope"), ProjectDashboardMetricDescriptor("Overloaded", fmt_int(len(overloaded)), "Above 100% capacity"), ProjectDashboardMetricDescriptor("At Risk", fmt_int(len(at_risk)), "90–100% utilization")),
        rows=tuple(ProjectDashboardPanelRowDescriptor(label=str(getattr(r, "resource_name", "") or "Resource"), value=fmt_percent(_util(r), 0), supporting_text=f"Capacity: {fmt_percent(getattr(r, 'capacity_percent', 100.0), 0)}", tone="danger" if _util(r) > 100.0 else "warning") for r in display),
    )


def _build_reports_panel(*, portfolio_mode: bool) -> ProjectDashboardPanelDescriptor:
    if portfolio_mode:
        return ProjectDashboardPanelDescriptor(title="Available Reports", subtitle="Report formats available for portfolio export.", rows=(ProjectDashboardPanelRowDescriptor("Portfolio Summary PDF", "Export", "Cross-project delivery summary report."), ProjectDashboardPanelRowDescriptor("Resource Utilization Excel", "Export", "Portfolio resource loading and capacity data.")))
    return ProjectDashboardPanelDescriptor(
        title="Available Reports", subtitle="Report formats available for this project.",
        rows=(
            ProjectDashboardPanelRowDescriptor("Gantt Chart (PNG)", "Export", "Schedule bar chart with critical path."),
            ProjectDashboardPanelRowDescriptor("EVM Curve (PNG)", "Export", "Planned value vs earned value vs actual cost trend."),
            ProjectDashboardPanelRowDescriptor("Full Project Report (Excel)", "Export", "Tasks, assignments, costs, and baseline in one workbook."),
            ProjectDashboardPanelRowDescriptor("Project Status Report (PDF)", "Export", "Formatted delivery status report for stakeholders."),
        ),
    )


__all__ = ["build_panels_from_dashboard_data", "build_preview_panels"]
