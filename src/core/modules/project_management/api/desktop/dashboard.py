from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from core.modules.project_management.services.baseline import BaselineService
from core.modules.project_management.services.dashboard import (
    PORTFOLIO_SCOPE_ID,
    DashboardService,
)
from core.modules.project_management.services.project.service import ProjectService
from core.modules.project_management.services.register.models import RegisterProjectSummary
from src.core.modules.project_management.domain.risk.register import (
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)


@dataclass(frozen=True)
class ProjectDashboardMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class ProjectDashboardOverviewDescriptor:
    title: str
    subtitle: str
    metrics: tuple[ProjectDashboardMetricDescriptor, ...]


@dataclass(frozen=True)
class ProjectDashboardSelectorOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectDashboardPanelRowDescriptor:
    label: str
    value: str
    supporting_text: str = ""
    tone: str = "default"


@dataclass(frozen=True)
class ProjectDashboardPanelDescriptor:
    title: str
    subtitle: str = ""
    hint: str = ""
    empty_state: str = ""
    rows: tuple["ProjectDashboardPanelRowDescriptor", ...] = field(default_factory=tuple)
    metrics: tuple["ProjectDashboardMetricDescriptor", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectDashboardChartPointDescriptor:
    label: str
    value: float
    value_label: str = ""
    supporting_text: str = ""
    target_value: float | None = None
    tone: str = "accent"


@dataclass(frozen=True)
class ProjectDashboardChartDescriptor:
    title: str
    subtitle: str = ""
    chart_type: str = "bar"
    empty_state: str = ""
    points: tuple["ProjectDashboardChartPointDescriptor", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectDashboardSectionItemDescriptor:
    id: str
    title: str
    status_label: str = ""
    subtitle: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardSectionDescriptor:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[ProjectDashboardSectionItemDescriptor, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectDashboardSnapshotDescriptor:
    overview: ProjectDashboardOverviewDescriptor
    project_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(
        default_factory=tuple
    )
    selected_project_id: str = ""
    baseline_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(
        default_factory=tuple
    )
    selected_baseline_id: str = ""
    panels: tuple[ProjectDashboardPanelDescriptor, ...] = field(default_factory=tuple)
    charts: tuple[ProjectDashboardChartDescriptor, ...] = field(default_factory=tuple)
    sections: tuple[ProjectDashboardSectionDescriptor, ...] = field(default_factory=tuple)
    empty_state: str = ""


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def _fmt_float(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return f"{0.0:,.{decimals}f}"


def _fmt_percent(value: Any, decimals: int = 2) -> str:
    return f"{_fmt_float(value, decimals)}%"


def _fmt_ratio(value: Any) -> str:
    if value is None:
        return "-"
    return _fmt_float(value, 2)


def _fmt_date(value: date | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.strftime("%Y-%m-%d")


class ProjectManagementDashboardDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        dashboard_service: DashboardService | None = None,
        baseline_service: BaselineService | None = None,
    ) -> None:
        self._project_service = project_service
        self._dashboard_service = dashboard_service
        self._baseline_service = baseline_service

    def build_empty_overview(self) -> ProjectDashboardOverviewDescriptor:
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
        self, *, project_name: str, dashboard_data: Any
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
                ProjectDashboardMetricDescriptor(
                    "Tasks",
                    f"{_fmt_int(tasks_completed)} / {_fmt_int(tasks_total)}",
                    "Done / Total",
                ),
                ProjectDashboardMetricDescriptor("Progress", _fmt_percent(progress), "Completion"),
                ProjectDashboardMetricDescriptor(
                    "In flight",
                    _fmt_int(getattr(kpi, "tasks_in_progress", 0)),
                    "Active work",
                ),
                ProjectDashboardMetricDescriptor(
                    "Blocked",
                    _fmt_int(getattr(kpi, "task_blocked", 0)),
                    "Needs action",
                ),
                ProjectDashboardMetricDescriptor(
                    "Critical",
                    _fmt_int(getattr(kpi, "critical_tasks", 0)),
                    "Path pressure",
                ),
                ProjectDashboardMetricDescriptor(
                    "Late",
                    _fmt_int(getattr(kpi, "late_tasks", 0)),
                    "Behind plan",
                ),
                ProjectDashboardMetricDescriptor(
                    "Cost variance",
                    _fmt_float(getattr(kpi, "cost_variance", 0.0)),
                    "Actual - Planned",
                ),
                ProjectDashboardMetricDescriptor(
                    "Spend vs plan",
                    (
                        f"{_fmt_float(getattr(kpi, 'total_actual_cost', 0.0), 0)} / "
                        f"{_fmt_float(getattr(kpi, 'total_planned_cost', 0.0), 0)}"
                    ),
                    "Actual / planned",
                ),
            ),
        )

    def build_snapshot(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
    ) -> ProjectDashboardSnapshotDescriptor:
        project_options = self._build_project_options()
        selected_project_id = self._resolve_project_id(project_id, project_options)
        baseline_options = self._build_baseline_options(selected_project_id)
        selected_baseline_id = self._resolve_baseline_id(baseline_id, baseline_options)
        if self._dashboard_service is None:
            return ProjectDashboardSnapshotDescriptor(
                overview=self.build_empty_overview(),
                project_options=project_options,
                selected_project_id=selected_project_id,
                baseline_options=baseline_options,
                selected_baseline_id=selected_baseline_id,
                panels=self._build_preview_panels(),
                charts=self._build_preview_charts(),
                sections=(
                    ProjectDashboardSectionDescriptor(
                        title="Dashboard Preview",
                        subtitle="Dashboard sections appear here once the PM dashboard desktop API is connected.",
                        empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
                    ),
                ),
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            )

        if selected_project_id == PORTFOLIO_SCOPE_ID:
            dashboard_data = self._dashboard_service.get_portfolio_data()
            return ProjectDashboardSnapshotDescriptor(
                overview=self.build_overview_from_dashboard_data(
                    project_name="Portfolio Overview",
                    dashboard_data=dashboard_data,
                ),
                project_options=project_options,
                selected_project_id=selected_project_id,
                baseline_options=baseline_options,
                selected_baseline_id=selected_baseline_id,
                panels=self._build_panels_from_dashboard_data(
                    dashboard_data=dashboard_data,
                    baseline_label="Portfolio view",
                    portfolio_mode=True,
                ),
                charts=self._build_charts_from_dashboard_data(
                    dashboard_data=dashboard_data,
                    portfolio_mode=True,
                ),
                sections=self._build_sections_from_dashboard_data(
                    dashboard_data=dashboard_data,
                    portfolio_mode=True,
                ),
                empty_state=(
                    "No project dashboard data is available yet."
                    if not getattr(dashboard_data, "portfolio", None)
                    or not getattr(dashboard_data.portfolio, "projects_total", 0)
                    else ""
                ),
            )

        project_label = self._project_label_for_id(selected_project_id, project_options)
        baseline_label = self._baseline_label_for_id(
            selected_baseline_id,
            baseline_options,
        )
        dashboard_data = self._dashboard_service.get_dashboard_data(
            selected_project_id,
            baseline_id=selected_baseline_id or None,
        )
        return ProjectDashboardSnapshotDescriptor(
            overview=self.build_overview_from_dashboard_data(
                project_name=project_label,
                dashboard_data=dashboard_data,
            ),
            project_options=project_options,
            selected_project_id=selected_project_id,
            baseline_options=baseline_options,
            selected_baseline_id=selected_baseline_id,
            panels=self._build_panels_from_dashboard_data(
                dashboard_data=dashboard_data,
                baseline_label=baseline_label,
                portfolio_mode=False,
            ),
            charts=self._build_charts_from_dashboard_data(
                dashboard_data=dashboard_data,
                portfolio_mode=False,
            ),
            sections=self._build_sections_from_dashboard_data(
                dashboard_data=dashboard_data,
                portfolio_mode=False,
            ),
            empty_state=(
                "Add tasks, baselines, and resource assignments to populate the dashboard sections."
            ),
        )

    def _build_project_options(self) -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
        options = [
            ProjectDashboardSelectorOptionDescriptor(
                value=PORTFOLIO_SCOPE_ID,
                label="Portfolio Overview",
            )
        ]
        if self._project_service is None:
            return tuple(options)
        try:
            projects = self._project_service.list_projects()
        except Exception:
            return tuple(options)
        options.extend(
            ProjectDashboardSelectorOptionDescriptor(value=project.id, label=project.name)
            for project in projects
        )
        return tuple(options)

    def _resolve_project_id(
        self,
        project_id: str | None,
        project_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
    ) -> str:
        normalized_id = (project_id or "").strip()
        option_values = {option.value for option in project_options}
        if normalized_id and normalized_id in option_values:
            return normalized_id
        for option in project_options:
            if option.value != PORTFOLIO_SCOPE_ID:
                return option.value
        return PORTFOLIO_SCOPE_ID

    def _build_baseline_options(
        self,
        selected_project_id: str,
    ) -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
        if selected_project_id == PORTFOLIO_SCOPE_ID:
            return (
                ProjectDashboardSelectorOptionDescriptor(
                    value="",
                    label="Portfolio view",
                ),
            )
        if self._baseline_service is None:
            return (
                ProjectDashboardSelectorOptionDescriptor(
                    value="",
                    label="Latest baseline",
                ),
            )
        try:
            baselines = self._baseline_service.list_baselines(selected_project_id)
        except Exception:
            return (
                ProjectDashboardSelectorOptionDescriptor(
                    value="",
                    label="Latest baseline",
                ),
            )
        return (
            ProjectDashboardSelectorOptionDescriptor(
                value="",
                label="Latest baseline",
            ),
            *(
                ProjectDashboardSelectorOptionDescriptor(
                    value=baseline.id,
                    label=f"{baseline.name} ({baseline.created_at.strftime('%Y-%m-%d %H:%M')})",
                )
                for baseline in baselines
            ),
        )

    @staticmethod
    def _resolve_baseline_id(
        baseline_id: str | None,
        baseline_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
    ) -> str:
        normalized_id = (baseline_id or "").strip()
        option_values = {option.value for option in baseline_options}
        if normalized_id in option_values:
            return normalized_id
        return ""

    @staticmethod
    def _project_label_for_id(
        project_id: str,
        project_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
    ) -> str:
        for option in project_options:
            if option.value == project_id:
                return option.label
        return "Dashboard"

    @staticmethod
    def _baseline_label_for_id(
        baseline_id: str,
        baseline_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
    ) -> str:
        for option in baseline_options:
            if option.value == baseline_id:
                return option.label
        if baseline_options:
            return baseline_options[0].label
        return "Latest baseline"

    def _build_preview_panels(self) -> tuple[ProjectDashboardPanelDescriptor, ...]:
        return (
            ProjectDashboardPanelDescriptor(
                title="Earned Value (EVM)",
                subtitle="Schedule and cost performance against the selected baseline.",
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            ),
            ProjectDashboardPanelDescriptor(
                title="Register Summary",
                subtitle="Risk, issue, and change pressure for the selected project.",
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            ),
            ProjectDashboardPanelDescriptor(
                title="Cost Sources",
                subtitle="Planned, committed, and actual cost-source visibility.",
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            ),
        )

    def _build_preview_charts(self) -> tuple[ProjectDashboardChartDescriptor, ...]:
        return (
            ProjectDashboardChartDescriptor(
                title="Burndown / Status Rollup",
                subtitle="Burndown or portfolio rollup appears here once the dashboard API is connected.",
                chart_type="line",
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            ),
            ProjectDashboardChartDescriptor(
                title="Resource Load",
                subtitle="Resource utilization bars appear here once the dashboard API is connected.",
                chart_type="bar",
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            ),
        )

    def _build_panels_from_dashboard_data(
        self,
        *,
        dashboard_data: Any,
        baseline_label: str,
        portfolio_mode: bool,
    ) -> tuple[ProjectDashboardPanelDescriptor, ...]:
        return (
            self._build_evm_panel(
                dashboard_data=dashboard_data,
                baseline_label=baseline_label,
                portfolio_mode=portfolio_mode,
            ),
            self._build_register_panel(
                dashboard_data=dashboard_data,
                portfolio_mode=portfolio_mode,
            ),
            self._build_cost_sources_panel(
                dashboard_data=dashboard_data,
                portfolio_mode=portfolio_mode,
            ),
        )

    def _build_charts_from_dashboard_data(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> tuple[ProjectDashboardChartDescriptor, ...]:
        return (
            self._build_burndown_chart(
                dashboard_data=dashboard_data,
                portfolio_mode=portfolio_mode,
            ),
            self._build_resource_chart(
                dashboard_data=dashboard_data,
                portfolio_mode=portfolio_mode,
            ),
        )

    def _build_sections_from_dashboard_data(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> tuple[ProjectDashboardSectionDescriptor, ...]:
        sections = [
            self._build_alert_section(dashboard_data),
            self._build_milestone_section(dashboard_data),
            self._build_critical_path_section(dashboard_data),
            self._build_upcoming_tasks_section(dashboard_data),
        ]
        if not portfolio_mode:
            sections.append(self._build_register_urgent_section(dashboard_data))
        if portfolio_mode:
            sections.append(self._build_portfolio_ranking_section(dashboard_data))
        return tuple(sections)

    def _build_alert_section(self, dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
        alerts = tuple(getattr(dashboard_data, "alerts", []) or [])
        return ProjectDashboardSectionDescriptor(
            title="Alerts",
            subtitle="Current project warnings and dashboard attention items.",
            empty_state="No active alerts right now.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=f"alert-{index}",
                    title=str(message),
                    status_label="Alert",
                    supporting_text="Generated from dashboard monitoring rules.",
                )
                for index, message in enumerate(alerts, start=1)
            ),
        )

    def _build_milestone_section(self, dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
        rows = tuple(getattr(dashboard_data, "milestone_health", []) or [])
        return ProjectDashboardSectionDescriptor(
            title="Milestones",
            subtitle="Key delivery checkpoints and schedule slip indicators.",
            empty_state="No milestone health rows are available yet.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=row.task_id,
                    title=row.task_name,
                    status_label=row.status_label,
                    subtitle=f"Owner: {row.owner_name or 'Unassigned'}",
                    supporting_text=f"Target: {_fmt_date(row.target_date)}",
                    meta_text=(
                        "On track"
                        if row.slip_days is None
                        else f"Slip: {row.slip_days} day(s)"
                    ),
                    state={"slipDays": row.slip_days},
                )
                for row in rows
            ),
        )

    def _build_critical_path_section(self, dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
        rows = tuple(getattr(dashboard_data, "critical_watchlist", []) or [])
        return ProjectDashboardSectionDescriptor(
            title="Critical Path",
            subtitle="Tasks with low float or schedule pressure.",
            empty_state="No critical-path watchlist items are available yet.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=row.task_id,
                    title=row.task_name,
                    status_label=row.status_label,
                    subtitle=f"Owner: {row.owner_name or 'Unassigned'}",
                    supporting_text=(
                        f"Finish: {_fmt_date(row.finish_date)} | "
                        f"Float: {_fmt_int(row.total_float_days or 0)} day(s)"
                    ),
                    meta_text=(
                        "On time"
                        if row.late_by_days in (None, 0)
                        else f"Late by {_fmt_int(row.late_by_days)} day(s)"
                    ),
                    state={"lateByDays": row.late_by_days},
                )
                for row in rows
            ),
        )

    def _build_upcoming_tasks_section(self, dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
        rows = tuple(getattr(dashboard_data, "upcoming_tasks", []) or [])
        return ProjectDashboardSectionDescriptor(
            title="Upcoming Work",
            subtitle="Tasks that are about to start or need immediate attention.",
            empty_state="No upcoming tasks are available yet.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=row.task_id,
                    title=row.name,
                    status_label=(
                        "Late"
                        if row.is_late
                        else "Critical"
                        if row.is_critical
                        else "Tracked"
                    ),
                    subtitle=(
                        f"Start: {_fmt_date(row.start_date)} | "
                        f"Finish: {_fmt_date(row.end_date)}"
                    ),
                    supporting_text=f"Owner: {row.main_resource or 'Unassigned'}",
                    meta_text=f"Progress: {_fmt_percent(row.percent_complete)}",
                    state={
                        "isLate": row.is_late,
                        "isCritical": row.is_critical,
                    },
                )
                for row in rows
            ),
        )

    def _build_register_urgent_section(self, dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
        summary = getattr(dashboard_data, "register_summary", None)
        urgent_items = tuple(getattr(summary, "urgent_items", []) or []) if summary is not None else ()
        return ProjectDashboardSectionDescriptor(
            title="Urgent Register Items",
            subtitle="Open risks, issues, and changes that need immediate attention.",
            empty_state="No urgent register items are active right now.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=item.entry_id,
                    title=item.title,
                    status_label=as_register_entry_severity(item.severity).value.title(),
                    subtitle=(
                        f"{as_register_entry_type(item.entry_type).value.title()} | "
                        f"Owner: {item.owner_name or 'Unassigned'}"
                    ),
                    supporting_text=f"Due: {_fmt_date(item.due_date)}",
                    meta_text=f"Status: {as_register_entry_status(item.status).value.replace('_', ' ').title()}",
                    state={
                        "entryType": as_register_entry_type(item.entry_type).value,
                        "severity": as_register_entry_severity(item.severity).value,
                        "status": as_register_entry_status(item.status).value,
                    },
                )
                for item in urgent_items
            ),
        )

    def _build_portfolio_ranking_section(
        self,
        dashboard_data: Any,
    ) -> ProjectDashboardSectionDescriptor:
        portfolio = getattr(dashboard_data, "portfolio", None)
        rankings = tuple(getattr(portfolio, "project_rankings", []) or [])
        return ProjectDashboardSectionDescriptor(
            title="Portfolio Ranking",
            subtitle="Cross-project pressure and risk ordering from the legacy dashboard.",
            empty_state="No portfolio ranking rows are available yet.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=row.project_id,
                    title=row.project_name,
                    status_label=row.project_status,
                    subtitle=(
                        f"Progress: {_fmt_percent(row.progress_percent)} | "
                        f"Late: {_fmt_int(row.late_tasks)} | Critical: {_fmt_int(row.critical_tasks)}"
                    ),
                    supporting_text=f"Risk score: {_fmt_float(row.risk_score)}",
                    meta_text=f"Cost variance: {_fmt_float(row.cost_variance)}",
                    state={"riskScore": row.risk_score},
                )
                for row in rankings
            ),
        )

    def _build_evm_panel(
        self,
        *,
        dashboard_data: Any,
        baseline_label: str,
        portfolio_mode: bool,
    ) -> ProjectDashboardPanelDescriptor:
        if portfolio_mode:
            return ProjectDashboardPanelDescriptor(
                title="Earned Value (EVM)",
                subtitle="Schedule and cost performance against the selected baseline.",
                empty_state="EVM remains project-scoped and is not rolled up in portfolio mode.",
            )

        evm = getattr(dashboard_data, "evm", None)
        if evm is None:
            return ProjectDashboardPanelDescriptor(
                title="Earned Value (EVM)",
                subtitle="Schedule and cost performance against the selected baseline.",
                empty_state="Create a baseline to enable EVM metrics for this dashboard.",
            )

        status_parts = [part.strip() for part in str(getattr(evm, "status_text", "") or "").split(".") if part.strip()]
        return ProjectDashboardPanelDescriptor(
            title="Earned Value (EVM)",
            subtitle="Schedule and cost performance against the selected baseline.",
            hint=f"As of {_fmt_date(evm.as_of)} (baseline: {baseline_label})",
            rows=(
                self._build_panel_row(
                    "Cost",
                    status_parts[0] if len(status_parts) > 0 else "-",
                ),
                self._build_panel_row(
                    "Schedule",
                    status_parts[1] if len(status_parts) > 1 else "-",
                ),
                self._build_panel_row(
                    "Forecast",
                    status_parts[2] if len(status_parts) > 2 else "-",
                ),
                self._build_panel_row(
                    "TCPI",
                    status_parts[3] if len(status_parts) > 3 else "-",
                ),
            ),
            metrics=(
                ProjectDashboardMetricDescriptor("CPI", _fmt_ratio(evm.CPI), "Cost performance"),
                ProjectDashboardMetricDescriptor("SPI", _fmt_ratio(evm.SPI), "Schedule performance"),
                ProjectDashboardMetricDescriptor("PV", _fmt_float(evm.PV), "Planned value"),
                ProjectDashboardMetricDescriptor("EV", _fmt_float(evm.EV), "Earned value"),
                ProjectDashboardMetricDescriptor("AC", _fmt_float(evm.AC), "Actual cost"),
                ProjectDashboardMetricDescriptor("EAC", _fmt_float(evm.EAC), "Estimate at completion"),
                ProjectDashboardMetricDescriptor("VAC", _fmt_float(evm.VAC), "Variance at completion"),
                ProjectDashboardMetricDescriptor("TCPI(BAC)", _fmt_ratio(evm.TCPI_to_BAC), "Needed to hit BAC"),
                ProjectDashboardMetricDescriptor("TCPI(EAC)", _fmt_ratio(evm.TCPI_to_EAC), "Needed to hit EAC"),
            ),
        )

    def _build_register_panel(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> ProjectDashboardPanelDescriptor:
        if portfolio_mode:
            return ProjectDashboardPanelDescriptor(
                title="Register Summary",
                subtitle="Risk, issue, and change pressure for the selected project.",
                empty_state="Register rollups remain project-scoped and are not summarized in portfolio mode.",
            )
        summary = getattr(dashboard_data, "register_summary", None)
        if summary is None:
            return ProjectDashboardPanelDescriptor(
                title="Register Summary",
                subtitle="Risk, issue, and change pressure for the selected project.",
                empty_state="No register summary is available yet for this project.",
            )
        return ProjectDashboardPanelDescriptor(
            title="Register Summary",
            subtitle="Risk, issue, and change pressure for the selected project.",
            rows=(
                ProjectDashboardPanelRowDescriptor(
                    "Open risks",
                    _fmt_int(summary.open_risks),
                    "Open register risks",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "Open issues",
                    _fmt_int(summary.open_issues),
                    "Open execution issues",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "Pending changes",
                    _fmt_int(summary.pending_changes),
                    "Changes awaiting closure",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "Overdue items",
                    _fmt_int(summary.overdue_items),
                    "Past due register entries",
                    tone="danger" if int(summary.overdue_items or 0) > 0 else "default",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "Critical items",
                    _fmt_int(summary.critical_items),
                    "Critical-severity register entries",
                    tone="danger" if int(summary.critical_items or 0) > 0 else "default",
                ),
            ),
        )

    def _build_cost_sources_panel(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> ProjectDashboardPanelDescriptor:
        if portfolio_mode:
            return ProjectDashboardPanelDescriptor(
                title="Cost Sources",
                subtitle="Planned, committed, and actual cost-source visibility.",
                empty_state="Cost-source breakdown remains project-scoped and is not summarized in portfolio mode.",
            )
        sources = getattr(dashboard_data, "cost_sources", None)
        rows = tuple(getattr(sources, "rows", []) or []) if sources is not None else ()
        if not rows:
            return ProjectDashboardPanelDescriptor(
                title="Cost Sources",
                subtitle="Planned, committed, and actual cost-source visibility.",
                empty_state="No cost-source breakdown is available yet for this project.",
            )
        return ProjectDashboardPanelDescriptor(
            title="Cost Sources",
            subtitle="Planned, committed, and actual cost-source visibility.",
            rows=tuple(
                ProjectDashboardPanelRowDescriptor(
                    label=row.source_label,
                    value=f"{_fmt_float(row.actual, 0)} / {_fmt_float(row.planned, 0)}",
                    supporting_text=f"Committed: {_fmt_float(row.committed, 0)}",
                    tone="warning" if float(row.actual or 0.0) > float(row.planned or 0.0) else "default",
                )
                for row in rows
            ),
        )

    def _build_burndown_chart(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> ProjectDashboardChartDescriptor:
        if portfolio_mode:
            portfolio = getattr(dashboard_data, "portfolio", None)
            rollup = tuple(getattr(portfolio, "status_rollup", []) or []) if portfolio is not None else ()
            return ProjectDashboardChartDescriptor(
                title="Portfolio Status Rollup",
                subtitle="Cross-project delivery status counts.",
                chart_type="bar",
                empty_state="No portfolio status data is available yet.",
                points=tuple(
                    ProjectDashboardChartPointDescriptor(
                        label=str(row.status_label or "").replace("_", " ").title(),
                        value=float(row.project_count or 0),
                        value_label=_fmt_int(row.project_count),
                        supporting_text="Projects",
                        tone="accent",
                    )
                    for row in rollup
                ),
            )

        points = tuple(getattr(dashboard_data, "burndown", []) or [])
        if not points:
            return ProjectDashboardChartDescriptor(
                title="Burndown",
                subtitle="Remaining tasks over time against the ideal trend.",
                chart_type="line",
                empty_state="No burndown data is available yet for this project.",
            )
        start_value = float(getattr(points[0], "remaining_tasks", 0) or 0)
        denominator = max(len(points) - 1, 1)
        return ProjectDashboardChartDescriptor(
            title="Burndown",
            subtitle="Remaining tasks over time against the ideal trend.",
            chart_type="line",
            points=tuple(
                ProjectDashboardChartPointDescriptor(
                    label=point.day.strftime("%m-%d"),
                    value=float(point.remaining_tasks or 0),
                    value_label=_fmt_int(point.remaining_tasks),
                    supporting_text=point.day.strftime("%Y-%m-%d"),
                    target_value=(start_value * (1.0 - (index / denominator))) if len(points) > 1 else 0.0,
                    tone="accent",
                )
                for index, point in enumerate(points)
            ),
        )

    def _build_resource_chart(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> ProjectDashboardChartDescriptor:
        rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
        if not rows:
            return ProjectDashboardChartDescriptor(
                title="Resource Load" if not portfolio_mode else "Cross-project Resource Load",
                subtitle="Peak utilization pressure across assigned resources.",
                chart_type="bar",
                empty_state="No resource-load data is available yet.",
            )
        return ProjectDashboardChartDescriptor(
            title="Resource Load" if not portfolio_mode else "Cross-project Resource Load",
            subtitle="Peak utilization pressure across assigned resources.",
            chart_type="bar",
            points=tuple(
                ProjectDashboardChartPointDescriptor(
                    label=row.resource_name,
                    value=float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0),
                    value_label=_fmt_percent(getattr(row, "utilization_percent", row.total_allocation_percent), 0),
                    supporting_text=(
                        f"Alloc {_fmt_float(row.total_allocation_percent, 0)}% / "
                        f"Cap {_fmt_float(row.capacity_percent, 0)}% | "
                        f"Tasks {_fmt_int(row.tasks_count)}"
                    ),
                    target_value=100.0,
                    tone=(
                        "danger"
                        if float(getattr(row, "utilization_percent", row.total_allocation_percent) or 0.0) > 100.0
                        else "accent"
                    ),
                )
                for row in rows[:8]
            ),
        )

    @staticmethod
    def _build_panel_row(label: str, text: str) -> ProjectDashboardPanelRowDescriptor:
        normalized = " ".join(str(text or "-").split())
        lowered = normalized.lower()
        tone = "default"
        if any(token in lowered for token in ("late", "over budget", "unfavorable", "above target")):
            tone = "danger"
        elif any(token in lowered for token in ("watch", "monitor", "attention", "recover")):
            tone = "warning"
        elif any(token in lowered for token in ("favorable", "ahead", "healthy", "within target")):
            tone = "success"
        return ProjectDashboardPanelRowDescriptor(label=label, value=normalized or "-", tone=tone)


def build_project_management_dashboard_desktop_api(
    *,
    project_service: ProjectService | None = None,
    dashboard_service: DashboardService | None = None,
    baseline_service: BaselineService | None = None,
) -> ProjectManagementDashboardDesktopApi:
    return ProjectManagementDashboardDesktopApi(
        project_service=project_service,
        dashboard_service=dashboard_service,
        baseline_service=baseline_service,
    )


__all__ = [
    "ProjectDashboardChartDescriptor",
    "ProjectDashboardChartPointDescriptor",
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectDashboardPanelDescriptor",
    "ProjectDashboardPanelRowDescriptor",
    "ProjectDashboardSectionDescriptor",
    "ProjectDashboardSectionItemDescriptor",
    "ProjectDashboardSelectorOptionDescriptor",
    "ProjectDashboardSnapshotDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
]
