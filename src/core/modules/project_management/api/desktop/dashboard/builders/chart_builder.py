"""Chart builders — EVM trend, burndown, resource load, portfolio charts."""

from __future__ import annotations
from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop.dashboard.models.charts import (
    ProjectDashboardChartDescriptor,
    ProjectDashboardChartPointDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.number_formatter import (
    fmt_float, fmt_int, fmt_percent,
)
from src.core.modules.project_management.api.desktop.dashboard.formatters.period_formatter import (
    fmt_period_axis_label, period_cutoff_date,
)

_PT = ProjectDashboardChartPointDescriptor


def build_preview_charts() -> tuple[ProjectDashboardChartDescriptor, ...]:
    _msg = "Project-management dashboard desktop API is not connected in this QML preview."
    return (
        ProjectDashboardChartDescriptor(title="Burndown / Status Rollup", subtitle="Burndown or portfolio rollup appears here once the dashboard API is connected.", chart_type="line", empty_state=_msg),
        ProjectDashboardChartDescriptor(title="Resource Load", subtitle="Resource utilization bars appear here once the dashboard API is connected.", chart_type="bar", empty_state=_msg),
    )


def build_charts_from_dashboard_data(
    *,
    dashboard_data: Any,
    selected_period_key: str,
    portfolio_mode: bool,
    reporting_service=None,
) -> tuple[ProjectDashboardChartDescriptor, ...]:
    if portfolio_mode:
        return (
            _build_portfolio_status_chart(dashboard_data=dashboard_data),
            _build_portfolio_cost_chart(dashboard_data=dashboard_data),
            _build_resource_chart(dashboard_data=dashboard_data, portfolio_mode=True),
        )
    return (
        _build_schedule_trend_chart(dashboard_data=dashboard_data, selected_period_key=selected_period_key, reporting_service=reporting_service),
        _build_cost_trend_chart(dashboard_data=dashboard_data, selected_period_key=selected_period_key, reporting_service=reporting_service),
        _build_resource_chart(dashboard_data=dashboard_data, portfolio_mode=False),
    )


def _filtered_evm_series(*, project_id: str, baseline_id: str | None, selected_period_key: str, reporting_service=None) -> tuple[Any, ...]:
    if reporting_service is None or not project_id:
        return ()
    try:
        get_series = getattr(reporting_service, "get_evm_series", None)
        if not callable(get_series):
            return ()
        series = tuple(get_series(project_id, baseline_id=baseline_id or None, as_of=date.today()) or ())
    except Exception:
        return ()
    cutoff = period_cutoff_date(selected_period_key)
    if cutoff is None:
        return series
    filtered = tuple(p for p in series if getattr(p, "period_end", cutoff) >= cutoff)
    return filtered or series[-6:]


def _build_portfolio_status_chart(*, dashboard_data: Any) -> ProjectDashboardChartDescriptor:
    portfolio = getattr(dashboard_data, "portfolio", None)
    rollup = tuple(getattr(portfolio, "status_rollup", []) or []) if portfolio is not None else ()
    return ProjectDashboardChartDescriptor(
        title="Portfolio Status", subtitle="Cross-project delivery status counts.", chart_type="bar",
        empty_state="No portfolio status data is available yet.",
        points=tuple(_PT(label=str(r.status_label or "").replace("_", " ").title(), value=float(r.project_count or 0), value_label=fmt_int(r.project_count), supporting_text="Projects", tone="accent") for r in rollup),
    )


def _build_portfolio_cost_chart(*, dashboard_data: Any) -> ProjectDashboardChartDescriptor:
    rankings = tuple(getattr(getattr(dashboard_data, "portfolio", None), "project_rankings", []) or [])
    return ProjectDashboardChartDescriptor(
        title="Cost Pressure", subtitle="Projects with the highest variance pressure.", chart_type="bar",
        empty_state="No project cost-pressure rows are available yet.",
        points=tuple(_PT(label=r.project_name, value=float(abs(r.cost_variance or 0.0)), value_label=fmt_float(r.cost_variance, 0), supporting_text=f"Late {fmt_int(r.late_tasks)} | Critical {fmt_int(r.critical_tasks)}", tone="danger" if float(r.cost_variance or 0.0) > 0.0 else "accent") for r in rankings[:8]),
    )


def _build_schedule_trend_chart(*, dashboard_data: Any, selected_period_key: str, reporting_service=None) -> ProjectDashboardChartDescriptor:
    project_id = str(getattr(getattr(dashboard_data, "kpi", None), "project_id", "") or "")
    baseline_id = getattr(getattr(dashboard_data, "evm", None), "baseline_id", None)
    series = _filtered_evm_series(project_id=project_id, baseline_id=baseline_id, selected_period_key=selected_period_key, reporting_service=reporting_service)
    if series:
        series_length = len(series)
        return ProjectDashboardChartDescriptor(
            title="Schedule Trend", subtitle="Earned value against planned value across the selected period.", chart_type="line",
            points=tuple(_PT(label=fmt_period_axis_label(p.period_end, selected_period_key=selected_period_key, series_length=series_length), value=float(p.EV or 0.0), value_label=fmt_float(p.EV, 0), supporting_text=p.period_end.strftime("%Y-%m-%d"), target_value=float(p.PV or 0.0), tone="danger" if float(p.SPI or 0.0) < 0.95 else "accent") for p in series),
        )
    return _build_burndown_fallback_chart(dashboard_data)


def _build_cost_trend_chart(*, dashboard_data: Any, selected_period_key: str, reporting_service=None) -> ProjectDashboardChartDescriptor:
    project_id = str(getattr(getattr(dashboard_data, "kpi", None), "project_id", "") or "")
    baseline_id = getattr(getattr(dashboard_data, "evm", None), "baseline_id", None)
    series = _filtered_evm_series(project_id=project_id, baseline_id=baseline_id, selected_period_key=selected_period_key, reporting_service=reporting_service)
    if series:
        series_length = len(series)
        return ProjectDashboardChartDescriptor(
            title="Cost Trend", subtitle="Actual cost against earned value across the selected period.", chart_type="line",
            points=tuple(_PT(label=fmt_period_axis_label(p.period_end, selected_period_key=selected_period_key, series_length=series_length), value=float(p.AC or 0.0), value_label=fmt_float(p.AC, 0), supporting_text=p.period_end.strftime("%Y-%m-%d"), target_value=float(p.EV or 0.0), tone="danger" if float(p.AC or 0.0) > float(p.EV or 0.0) else "accent") for p in series),
        )
    sources = getattr(dashboard_data, "cost_sources", None)
    source_rows = tuple(getattr(sources, "rows", []) or []) if sources is not None else ()
    return ProjectDashboardChartDescriptor(
        title="Cost Trend", subtitle="Actual cost against planned budget lines.", chart_type="bar",
        empty_state="No cost-trend data is available yet for this project.",
        points=tuple(_PT(label=r.source_label, value=float(r.actual or 0.0), value_label=fmt_float(r.actual, 0), supporting_text=f"Planned {fmt_float(r.planned, 0)}", target_value=float(r.planned or 0.0), tone="danger" if float(r.actual or 0.0) > float(r.planned or 0.0) else "accent") for r in source_rows[:8]),
    )


def _build_burndown_fallback_chart(dashboard_data: Any) -> ProjectDashboardChartDescriptor:
    points = tuple(getattr(dashboard_data, "burndown", []) or [])
    if not points:
        return ProjectDashboardChartDescriptor(title="Schedule Trend", subtitle="Remaining tasks over time against the ideal trend.", chart_type="line", empty_state="No schedule-trend data is available yet for this project.")
    start_value = float(getattr(points[0], "remaining_tasks", 0) or 0)
    denominator = max(len(points) - 1, 1)
    return ProjectDashboardChartDescriptor(
        title="Schedule Trend", subtitle="Remaining tasks over time against the ideal trend.", chart_type="line",
        points=tuple(_PT(label=p.day.strftime("%d %b"), value=float(p.remaining_tasks or 0), value_label=fmt_int(p.remaining_tasks), supporting_text=p.day.strftime("%Y-%m-%d"), target_value=(start_value * (1.0 - (idx / denominator))) if len(points) > 1 else 0.0, tone="accent") for idx, p in enumerate(points)),
    )


def _build_resource_chart(*, dashboard_data: Any, portfolio_mode: bool) -> ProjectDashboardChartDescriptor:
    rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
    title = "Cross-project Resource Load" if portfolio_mode else "Resource Load"
    subtitle = "Peak utilization pressure across assigned resources."
    if not rows:
        return ProjectDashboardChartDescriptor(title=title, subtitle=subtitle, chart_type="bar", empty_state="No resource-load data is available yet.")

    def _util(r):
        return float(getattr(r, "utilization_percent", r.total_allocation_percent) or 0.0)

    return ProjectDashboardChartDescriptor(
        title=title, subtitle=subtitle, chart_type="bar",
        points=tuple(_PT(label=r.resource_name, value=_util(r), value_label=fmt_percent(_util(r), 0), supporting_text=f"Alloc {fmt_float(r.total_allocation_percent, 0)}% / Cap {fmt_float(r.capacity_percent, 0)}% | Tasks {fmt_int(r.tasks_count)}", target_value=100.0, tone="danger" if _util(r) > 100.0 else "accent") for r in rows[:8]),
    )


__all__ = ["build_charts_from_dashboard_data", "build_preview_charts"]
