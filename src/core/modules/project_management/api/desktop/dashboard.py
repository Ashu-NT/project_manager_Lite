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
            self._build_resource_load_section(dashboard_data),
            self._build_upcoming_tasks_section(dashboard_data),
        ]
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

    def _build_resource_load_section(self, dashboard_data: Any) -> ProjectDashboardSectionDescriptor:
        rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
        return ProjectDashboardSectionDescriptor(
            title="Resource Load",
            subtitle="Peak allocation pressure across assigned resources.",
            empty_state="No resource-load rows are available yet.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=row.resource_id,
                    title=row.resource_name,
                    status_label=_fmt_percent(row.utilization_percent),
                    subtitle=(
                        f"Allocation: {_fmt_float(row.total_allocation_percent, 0)}% | "
                        f"Capacity: {_fmt_float(row.capacity_percent, 0)}%"
                    ),
                    supporting_text=f"Assignments: {_fmt_int(row.tasks_count)}",
                    meta_text=(
                        "Overloaded"
                        if float(getattr(row, "utilization_percent", 0.0) or 0.0) > 100.0
                        else "Within capacity"
                    ),
                    state={"utilizationPercent": row.utilization_percent},
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
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectDashboardSectionDescriptor",
    "ProjectDashboardSectionItemDescriptor",
    "ProjectDashboardSelectorOptionDescriptor",
    "ProjectDashboardSnapshotDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
]
