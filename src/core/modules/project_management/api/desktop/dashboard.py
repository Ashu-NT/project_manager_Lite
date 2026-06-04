from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.dashboard import (
    PORTFOLIO_SCOPE_ID,
    DashboardService,
)
from src.core.modules.project_management.application.risk import (
    RegisterProjectSummary,
    RegisterService,
)
from src.core.modules.project_management.application.collaboration import CollaborationService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
    as_register_entry_severity,
    as_register_entry_status,
    as_register_entry_type,
)
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.platform.approval import ApprovalService
from src.core.platform.approval.domain import ApprovalStatus


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
class ProjectDashboardHealthCardDescriptor:
    id: str
    title: str
    status_label: str = ""
    metric_value: str = ""
    metric_label: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    tone: str = "default"
    route_id: str = ""


@dataclass(frozen=True)
class ProjectDashboardOperationalTabDescriptor:
    id: str
    label: str
    count: int = 0
    route_id: str = ""


@dataclass(frozen=True)
class ProjectDashboardTableColumnDescriptor:
    key: str
    label: str
    flex: int = 1
    min_width: int = 120
    sortable: bool = False
    visible: bool = True
    column_type: str = "text"


@dataclass(frozen=True)
class ProjectDashboardTableRowDescriptor:
    id: str
    values: dict[str, Any] = field(default_factory=dict)
    route_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardOperationalTableDescriptor:
    id: str
    title: str
    subtitle: str = ""
    empty_state: str = ""
    columns: tuple[ProjectDashboardTableColumnDescriptor, ...] = field(
        default_factory=tuple
    )
    rows: tuple[ProjectDashboardTableRowDescriptor, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectDashboardActivityItemDescriptor:
    id: str
    title: str
    status_label: str = ""
    meta_text: str = ""
    route_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardActivityFeedDescriptor:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[ProjectDashboardActivityItemDescriptor, ...] = field(
        default_factory=tuple
    )


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
    period_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(
        default_factory=tuple
    )
    selected_period_key: str = ""
    view_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(
        default_factory=tuple
    )
    selected_view_key: str = ""
    health_cards: tuple[ProjectDashboardHealthCardDescriptor, ...] = field(
        default_factory=tuple
    )
    operational_tabs: tuple[ProjectDashboardOperationalTabDescriptor, ...] = field(
        default_factory=tuple
    )
    operational_tables: tuple[ProjectDashboardOperationalTableDescriptor, ...] = field(
        default_factory=tuple
    )
    activity_feed: ProjectDashboardActivityFeedDescriptor | None = None
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


def _fmt_period_axis_label(
    period_end: date,
    *,
    selected_period_key: str,
    series_length: int,
) -> str:
    normalized_key = (selected_period_key or "").strip().lower()
    if normalized_key in {"30d", "60d", "90d"}:
        return period_end.strftime("%d %b")
    if normalized_key == "180d":
        return period_end.strftime("%b %Y" if series_length > 6 else "%d %b")
    return period_end.strftime("%b %Y")


def _coerce_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _fmt_utc_datetime(value: datetime | None) -> str:
    resolved = _coerce_utc_datetime(value)
    if resolved is None:
        return ""
    return resolved.strftime("%Y-%m-%d %H:%M")


class ProjectManagementDashboardDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        dashboard_service: DashboardService | None = None,
        baseline_service: BaselineService | None = None,
        reporting_service: ReportingService | None = None,
        register_service: RegisterService | None = None,
        collaboration_service: CollaborationService | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self._project_service = project_service
        self._dashboard_service = dashboard_service
        self._baseline_service = baseline_service
        self._reporting_service = reporting_service
        self._register_service = register_service
        self._collaboration_service = collaboration_service
        self._approval_service = approval_service

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
        period_key: str | None = None,
        view_key: str | None = None,
    ) -> ProjectDashboardSnapshotDescriptor:
        project_options = self._build_project_options()
        selected_project_id = self._resolve_project_id(project_id, project_options)
        baseline_options = self._build_baseline_options(selected_project_id)
        selected_baseline_id = self._resolve_baseline_id(baseline_id, baseline_options)
        period_options = self._build_period_options()
        selected_period_key = self._resolve_period_key(period_key, period_options)
        view_options = self._build_view_options()
        selected_view_key = self._resolve_view_key(view_key, view_options)
        if self._dashboard_service is None:
            preview_tables = self._build_preview_operational_tables()
            return ProjectDashboardSnapshotDescriptor(
                overview=self.build_empty_overview(),
                project_options=project_options,
                selected_project_id=selected_project_id,
                baseline_options=baseline_options,
                selected_baseline_id=selected_baseline_id,
                period_options=period_options,
                selected_period_key=selected_period_key,
                view_options=view_options,
                selected_view_key=selected_view_key,
                health_cards=self._build_preview_health_cards(),
                operational_tabs=self._build_operational_tabs(preview_tables),
                operational_tables=preview_tables,
                activity_feed=self._build_preview_activity_feed(),
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

        portfolio_mode = selected_project_id == PORTFOLIO_SCOPE_ID
        if portfolio_mode:
            dashboard_data = self._dashboard_service.get_portfolio_data()
            pending_approvals = self._list_pending_approvals(project_id=None)
            activity_feed = self._build_activity_feed(
                project_id=None,
                selected_period_key=selected_period_key,
                portfolio_mode=True,
            )
            operational_tables = self._build_operational_tables(
                dashboard_data=dashboard_data,
                pending_approvals=pending_approvals,
                selected_period_key=selected_period_key,
                portfolio_mode=True,
            )
            return ProjectDashboardSnapshotDescriptor(
                overview=self._build_contextual_overview(
                    project_name="Portfolio Overview",
                    dashboard_data=dashboard_data,
                    pending_approval_count=len(pending_approvals),
                    selected_view_key=selected_view_key,
                    portfolio_mode=True,
                ),
                project_options=project_options,
                selected_project_id=selected_project_id,
                baseline_options=baseline_options,
                selected_baseline_id=selected_baseline_id,
                period_options=period_options,
                selected_period_key=selected_period_key,
                view_options=view_options,
                selected_view_key=selected_view_key,
                health_cards=self._build_health_cards(
                    dashboard_data=dashboard_data,
                    pending_approvals=pending_approvals,
                    portfolio_mode=True,
                    project_id=None,
                ),
                operational_tabs=self._build_operational_tabs(operational_tables),
                operational_tables=operational_tables,
                activity_feed=activity_feed,
                panels=self._build_panels_from_dashboard_data(
                    dashboard_data=dashboard_data,
                    baseline_label="Portfolio view",
                    selected_baseline_id="",
                    portfolio_mode=True,
                ),
                charts=self._build_charts_from_dashboard_data(
                    dashboard_data=dashboard_data,
                    selected_period_key=selected_period_key,
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
        pending_approvals = self._list_pending_approvals(project_id=selected_project_id)
        activity_feed = self._build_activity_feed(
            project_id=selected_project_id,
            selected_period_key=selected_period_key,
            portfolio_mode=False,
        )
        operational_tables = self._build_operational_tables(
            dashboard_data=dashboard_data,
            pending_approvals=pending_approvals,
            selected_period_key=selected_period_key,
            portfolio_mode=False,
        )
        return ProjectDashboardSnapshotDescriptor(
            overview=self._build_contextual_overview(
                project_name=project_label,
                dashboard_data=dashboard_data,
                pending_approval_count=len(pending_approvals),
                selected_view_key=selected_view_key,
                portfolio_mode=False,
            ),
            project_options=project_options,
            selected_project_id=selected_project_id,
            baseline_options=baseline_options,
            selected_baseline_id=selected_baseline_id,
            period_options=period_options,
            selected_period_key=selected_period_key,
            view_options=view_options,
            selected_view_key=selected_view_key,
            health_cards=self._build_health_cards(
                dashboard_data=dashboard_data,
                pending_approvals=pending_approvals,
                portfolio_mode=False,
                project_id=selected_project_id,
            ),
            operational_tabs=self._build_operational_tabs(operational_tables),
            operational_tables=operational_tables,
            activity_feed=activity_feed,
            panels=self._build_panels_from_dashboard_data(
                dashboard_data=dashboard_data,
                baseline_label=baseline_label,
                selected_baseline_id=selected_baseline_id,
                portfolio_mode=False,
            ),
            charts=self._build_charts_from_dashboard_data(
                dashboard_data=dashboard_data,
                selected_period_key=selected_period_key,
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

    @staticmethod
    def _build_period_options() -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
        return (
            ProjectDashboardSelectorOptionDescriptor("all", "All Horizon"),
            ProjectDashboardSelectorOptionDescriptor("30d", "30 Days"),
            ProjectDashboardSelectorOptionDescriptor("60d", "60 Days"),
            ProjectDashboardSelectorOptionDescriptor("90d", "90 Days"),
            ProjectDashboardSelectorOptionDescriptor("180d", "180 Days"),
        )

    @staticmethod
    def _resolve_period_key(
        period_key: str | None,
        period_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
    ) -> str:
        normalized_key = (period_key or "").strip().lower()
        option_values = {option.value for option in period_options}
        if normalized_key in option_values:
            return normalized_key
        return "90d"

    @staticmethod
    def _build_view_options() -> tuple[ProjectDashboardSelectorOptionDescriptor, ...]:
        return (
            ProjectDashboardSelectorOptionDescriptor("executive", "Executive View"),
            ProjectDashboardSelectorOptionDescriptor("pmo", "PMO View"),
            ProjectDashboardSelectorOptionDescriptor(
                "project_manager", "Project Manager View"
            ),
            ProjectDashboardSelectorOptionDescriptor(
                "resource_manager", "Resource Manager View"
            ),
            ProjectDashboardSelectorOptionDescriptor("financial", "Financial View"),
        )

    @staticmethod
    def _resolve_view_key(
        view_key: str | None,
        view_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...],
    ) -> str:
        normalized_key = (view_key or "").strip().lower()
        option_values = {option.value for option in view_options}
        if normalized_key in option_values:
            return normalized_key
        return "executive"

    def _build_contextual_overview(
        self,
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
            portfolio = getattr(dashboard_data, "portfolio", None)
            total_projects = int(getattr(portfolio, "projects_total", 0) or 0)
            active_projects = int(getattr(portfolio, "active_projects", 0) or 0)
            at_risk_projects = int(getattr(portfolio, "at_risk_projects", 0) or 0)
            on_hold_projects = int(getattr(portfolio, "on_hold_projects", 0) or 0)
            on_track_projects = max(total_projects - at_risk_projects - on_hold_projects, 0)
            open_tasks = max(
                int(getattr(kpi, "tasks_total", 0) or 0)
                - int(getattr(kpi, "tasks_completed", 0) or 0),
                0,
            )
            utilization = self._average_utilization_percent(
                tuple(getattr(dashboard_data, "resource_load", []) or [])
            )
            metrics_by_id = {
                "total_projects": ProjectDashboardMetricDescriptor(
                    "Total Projects",
                    _fmt_int(total_projects),
                    "Portfolio footprint",
                ),
                "active_projects": ProjectDashboardMetricDescriptor(
                    "Active",
                    _fmt_int(active_projects),
                    "Projects currently executing",
                ),
                "on_track": ProjectDashboardMetricDescriptor(
                    "On Track",
                    _fmt_int(on_track_projects),
                    "Projects without current risk flags",
                ),
                "delayed": ProjectDashboardMetricDescriptor(
                    "Delayed",
                    _fmt_int(getattr(kpi, "late_tasks", 0)),
                    "Late tasks across visible projects",
                ),
                "budget_variance": ProjectDashboardMetricDescriptor(
                    "Budget Var.",
                    _fmt_float(getattr(kpi, "cost_variance", 0.0), 0),
                    "Portfolio actual minus planned",
                ),
                "high_risks": ProjectDashboardMetricDescriptor(
                    "At Risk",
                    _fmt_int(at_risk_projects),
                    "Projects requiring intervention",
                ),
                "open_tasks": ProjectDashboardMetricDescriptor(
                    "Open Tasks",
                    _fmt_int(open_tasks),
                    "Tasks not yet complete",
                ),
                "utilization": ProjectDashboardMetricDescriptor(
                    "Utilization",
                    _fmt_percent(utilization, 0),
                    "Average visible resource load",
                ),
                "pending_approvals": ProjectDashboardMetricDescriptor(
                    "Approvals",
                    _fmt_int(pending_approval_count),
                    "Pending governed changes",
                ),
                "critical_tasks": ProjectDashboardMetricDescriptor(
                    "Critical",
                    _fmt_int(getattr(kpi, "critical_tasks", 0)),
                    "Critical tasks across visible projects",
                ),
            }
            subtitle = {
                "executive": "Executive portfolio command center",
                "pmo": "PMO portfolio operations and escalation view",
                "project_manager": "Cross-project delivery control view",
                "resource_manager": "Cross-project resource pressure view",
                "financial": "Portfolio financial control view",
            }.get(selected_view_key, "Executive portfolio command center")
            metric_order = {
                "executive": (
                    "total_projects",
                    "active_projects",
                    "on_track",
                    "delayed",
                    "budget_variance",
                    "high_risks",
                    "open_tasks",
                    "utilization",
                ),
                "pmo": (
                    "active_projects",
                    "on_track",
                    "delayed",
                    "critical_tasks",
                    "high_risks",
                    "pending_approvals",
                    "open_tasks",
                    "utilization",
                ),
                "project_manager": (
                    "active_projects",
                    "delayed",
                    "critical_tasks",
                    "high_risks",
                    "open_tasks",
                    "pending_approvals",
                    "utilization",
                    "budget_variance",
                ),
                "resource_manager": (
                    "active_projects",
                    "utilization",
                    "open_tasks",
                    "delayed",
                    "critical_tasks",
                    "high_risks",
                    "pending_approvals",
                    "budget_variance",
                ),
                "financial": (
                    "budget_variance",
                    "pending_approvals",
                    "active_projects",
                    "delayed",
                    "open_tasks",
                    "high_risks",
                    "utilization",
                    "total_projects",
                ),
            }.get(selected_view_key, ())
            return ProjectDashboardOverviewDescriptor(
                title=title,
                subtitle=subtitle,
                metrics=tuple(metrics_by_id[key] for key in metric_order if key in metrics_by_id),
            )

        evm = getattr(dashboard_data, "evm", None)
        summary = getattr(dashboard_data, "register_summary", None)
        tasks_total = int(getattr(kpi, "tasks_total", 0) or 0)
        tasks_completed = int(getattr(kpi, "tasks_completed", 0) or 0)
        open_tasks = max(tasks_total - tasks_completed, 0)
        progress = 100.0 * tasks_completed / tasks_total if tasks_total else 0.0
        utilization = self._average_utilization_percent(
            tuple(getattr(dashboard_data, "resource_load", []) or [])
        )
        overloads = self._overloaded_resource_count(
            tuple(getattr(dashboard_data, "resource_load", []) or [])
        )
        metrics_by_id = {
            "progress": ProjectDashboardMetricDescriptor(
                "Progress",
                _fmt_percent(progress, 0),
                "Project completion",
            ),
            "spi": ProjectDashboardMetricDescriptor(
                "SPI",
                _fmt_ratio(getattr(evm, "SPI", None)),
                "Schedule performance index",
            ),
            "cpi": ProjectDashboardMetricDescriptor(
                "CPI",
                _fmt_ratio(getattr(evm, "CPI", None)),
                "Cost performance index",
            ),
            "budget_variance": ProjectDashboardMetricDescriptor(
                "Budget Var.",
                _fmt_float(getattr(kpi, "cost_variance", 0.0), 0),
                "Actual minus planned cost",
            ),
            "forecast_variance": ProjectDashboardMetricDescriptor(
                "Forecast Var.",
                _fmt_float(getattr(evm, "VAC", 0.0), 0),
                "Variance at completion",
            ),
            "high_risks": ProjectDashboardMetricDescriptor(
                "High Risks",
                _fmt_int(getattr(summary, "critical_items", 0) or 0),
                "Critical register exposure",
            ),
            "open_tasks": ProjectDashboardMetricDescriptor(
                "Open Tasks",
                _fmt_int(open_tasks),
                "Tasks not yet complete",
            ),
            "pending_approvals": ProjectDashboardMetricDescriptor(
                "Approvals",
                _fmt_int(pending_approval_count),
                "Pending governed changes",
            ),
            "utilization": ProjectDashboardMetricDescriptor(
                "Utilization",
                _fmt_percent(utilization, 0),
                (
                    f"{_fmt_int(overloads)} overloaded resource(s)"
                    if overloads
                    else "Resource load within capacity"
                ),
            ),
            "delayed": ProjectDashboardMetricDescriptor(
                "Delayed",
                _fmt_int(getattr(kpi, "late_tasks", 0)),
                "Tasks behind target dates",
            ),
            "critical_tasks": ProjectDashboardMetricDescriptor(
                "Critical",
                _fmt_int(getattr(kpi, "critical_tasks", 0)),
                "Critical-path tasks",
            ),
        }
        subtitle = {
            "executive": "Executive project command center",
            "pmo": "PMO project health and escalation view",
            "project_manager": "Project manager delivery-control view",
            "resource_manager": "Resource loading and capacity control view",
            "financial": "Project financial control view",
        }.get(selected_view_key, "Executive project command center")
        metric_order = {
            "executive": (
                "progress",
                "spi",
                "cpi",
                "budget_variance",
                "forecast_variance",
                "high_risks",
                "open_tasks",
                "utilization",
            ),
            "pmo": (
                "progress",
                "delayed",
                "critical_tasks",
                "high_risks",
                "pending_approvals",
                "open_tasks",
                "spi",
                "cpi",
            ),
            "project_manager": (
                "progress",
                "delayed",
                "critical_tasks",
                "open_tasks",
                "high_risks",
                "pending_approvals",
                "utilization",
                "spi",
            ),
            "resource_manager": (
                "utilization",
                "open_tasks",
                "delayed",
                "critical_tasks",
                "progress",
                "pending_approvals",
                "high_risks",
                "budget_variance",
            ),
            "financial": (
                "budget_variance",
                "forecast_variance",
                "cpi",
                "spi",
                "pending_approvals",
                "high_risks",
                "open_tasks",
                "progress",
            ),
        }.get(selected_view_key, ())
        return ProjectDashboardOverviewDescriptor(
            title=title,
            subtitle=subtitle,
            metrics=tuple(metrics_by_id[key] for key in metric_order if key in metrics_by_id),
        )

    @staticmethod
    def _average_utilization_percent(rows: tuple[Any, ...]) -> float:
        if not rows:
            return 0.0
        values = [
            float(getattr(row, "utilization_percent", getattr(row, "total_allocation_percent", 0.0)) or 0.0)
            for row in rows
        ]
        return sum(values) / max(len(values), 1)

    @staticmethod
    def _peak_utilization_percent(rows: tuple[Any, ...]) -> float:
        if not rows:
            return 0.0
        return max(
            float(getattr(row, "utilization_percent", getattr(row, "total_allocation_percent", 0.0)) or 0.0)
            for row in rows
        )

    @staticmethod
    def _overloaded_resource_count(rows: tuple[Any, ...]) -> int:
        return sum(
            1
            for row in rows
            if float(getattr(row, "utilization_percent", getattr(row, "total_allocation_percent", 0.0)) or 0.0)
            > 100.0
        )

    @staticmethod
    def _period_cutoff_date(selected_period_key: str) -> date | None:
        days_by_key = {"30d": 30, "60d": 60, "90d": 90, "180d": 180}
        days = days_by_key.get((selected_period_key or "").strip().lower())
        if days is None:
            return None
        return date.today() - timedelta(days=days)

    @staticmethod
    def _period_cutoff_datetime(selected_period_key: str) -> datetime | None:
        cutoff = ProjectManagementDashboardDesktopApi._period_cutoff_date(
            selected_period_key
        )
        if cutoff is None:
            return None
        return datetime.combine(cutoff, datetime.min.time(), tzinfo=timezone.utc)

    def _build_preview_health_cards(
        self,
    ) -> tuple[ProjectDashboardHealthCardDescriptor, ...]:
        return (
            ProjectDashboardHealthCardDescriptor(
                id="schedule",
                title="Schedule Health",
                status_label="Preview",
                metric_value="SPI -",
                metric_label="Performance",
                supporting_text="Schedule diagnostics appear when the dashboard API is connected.",
                route_id="project_management.scheduling",
            ),
            ProjectDashboardHealthCardDescriptor(
                id="cost",
                title="Cost Health",
                status_label="Preview",
                metric_value="CPI -",
                metric_label="Performance",
                supporting_text="Cost diagnostics appear when the dashboard API is connected.",
                route_id="project_management.financials",
            ),
            ProjectDashboardHealthCardDescriptor(
                id="risk",
                title="Risk Exposure",
                status_label="Preview",
                metric_value="0",
                metric_label="Critical items",
                supporting_text="Risk exposure appears when the dashboard API is connected.",
                route_id="project_management.risk",
            ),
            ProjectDashboardHealthCardDescriptor(
                id="resource",
                title="Resource Health",
                status_label="Preview",
                metric_value="0%",
                metric_label="Utilization",
                supporting_text="Resource loading appears when the dashboard API is connected.",
                route_id="project_management.resources",
            ),
        )

    def _build_preview_operational_tables(
        self,
    ) -> tuple[ProjectDashboardOperationalTableDescriptor, ...]:
        preview_columns = (
            ProjectDashboardTableColumnDescriptor(
                key="title",
                label="Item",
                flex=3,
                min_width=220,
                sortable=True,
            ),
            ProjectDashboardTableColumnDescriptor(
                key="statusLabel",
                label="Status",
                flex=0,
                min_width=96,
                sortable=False,
                column_type="status",
            ),
            ProjectDashboardTableColumnDescriptor(
                key="summary",
                label="Summary",
                flex=2,
                min_width=180,
            ),
        )
        return (
            ProjectDashboardOperationalTableDescriptor(
                id="delayed_tasks",
                title="Delayed Tasks",
                subtitle="Operational rows appear here when the dashboard API is connected.",
                empty_state="No delayed-task rows are available in preview mode.",
                columns=preview_columns,
            ),
        )

    def _build_preview_activity_feed(self) -> ProjectDashboardActivityFeedDescriptor:
        return ProjectDashboardActivityFeedDescriptor(
            title="Recent Activity",
            subtitle="Activity feed appears here when the dashboard API is connected.",
            empty_state="No recent dashboard activity is available in preview mode.",
        )

    def _build_preview_panels(self) -> tuple[ProjectDashboardPanelDescriptor, ...]:
        _preview_msg = "Project-management dashboard desktop API is not connected in this QML preview."
        return (
            ProjectDashboardPanelDescriptor(
                title="Earned Value (EVM)",
                subtitle="Schedule and cost performance against the selected baseline.",
                empty_state=_preview_msg,
            ),
            ProjectDashboardPanelDescriptor(
                title="Register Summary",
                subtitle="Risk, issue, and change pressure for the selected project.",
                empty_state=_preview_msg,
            ),
            ProjectDashboardPanelDescriptor(
                title="Cost Sources",
                subtitle="Planned, committed, and actual cost-source visibility.",
                empty_state=_preview_msg,
            ),
            ProjectDashboardPanelDescriptor(
                title="Baseline Variance",
                subtitle="Task schedule and cost drift between baselines.",
                empty_state=_preview_msg,
            ),
            ProjectDashboardPanelDescriptor(
                title="Resource Overloads",
                subtitle="Resources that exceed capacity across assigned activities.",
                empty_state=_preview_msg,
            ),
            ProjectDashboardPanelDescriptor(
                title="Available Reports",
                subtitle="Report formats available for this project.",
                empty_state=_preview_msg,
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

    def _build_baseline_variance_card(
        self,
        project_id: str | None,
    ) -> ProjectDashboardHealthCardDescriptor:
        if not project_id or self._baseline_service is None:
            return ProjectDashboardHealthCardDescriptor(
                id="baseline_variance",
                title="Baseline Variance",
                status_label="No Baseline",
                metric_value="—",
                metric_label="Tasks behind plan",
                supporting_text="Approve a baseline in the Scheduling workspace to track drift.",
                meta_text="Baseline variance tracking inactive.",
                tone="default",
                route_id="project_management.scheduling",
            )
        try:
            approved = self._baseline_service.get_approved_baseline(project_id)
        except Exception:
            approved = None
        if approved is None:
            return ProjectDashboardHealthCardDescriptor(
                id="baseline_variance",
                title="Baseline Variance",
                status_label="No Baseline",
                metric_value="—",
                metric_label="Tasks behind plan",
                supporting_text="No approved baseline for this project yet.",
                meta_text="Approve a baseline to enable variance tracking.",
                tone="default",
                route_id="project_management.scheduling",
            )
        try:
            records = tuple(self._baseline_service.list_variance_records(approved.id) or [])
        except Exception:
            records = ()
        behind = sum(1 for r in records if getattr(r, "finish_variance_days", 0) > 0)
        ahead = sum(1 for r in records if getattr(r, "finish_variance_days", 0) < 0)
        on_track = len(records) - behind - ahead
        tone = "danger" if behind > 0 else "success"
        status = "Behind" if behind > 0 else "On Track"
        return ProjectDashboardHealthCardDescriptor(
            id="baseline_variance",
            title="Baseline Variance",
            status_label=status,
            metric_value=_fmt_int(behind),
            metric_label="Tasks behind plan",
            supporting_text=f"Ahead: {_fmt_int(ahead)} | On track: {_fmt_int(on_track)} | Behind: {_fmt_int(behind)}",
            meta_text=f"vs. {getattr(approved, 'name', 'approved baseline')}",
            tone=tone,
            route_id="project_management.scheduling",
        )

    def _build_health_cards(
        self,
        *,
        dashboard_data: Any,
        pending_approvals: tuple[Any, ...],
        portfolio_mode: bool,
        project_id: str | None = None,
    ) -> tuple[ProjectDashboardHealthCardDescriptor, ...]:
        kpi = getattr(dashboard_data, "kpi", None)
        evm = getattr(dashboard_data, "evm", None)
        summary = getattr(dashboard_data, "register_summary", None)
        resource_rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
        peak_utilization = self._peak_utilization_percent(resource_rows)
        overloads = self._overloaded_resource_count(resource_rows)

        if portfolio_mode:
            portfolio = getattr(dashboard_data, "portfolio", None)
            total_projects = int(getattr(portfolio, "projects_total", 0) or 0)
            at_risk_projects = int(getattr(portfolio, "at_risk_projects", 0) or 0)
            active_projects = int(getattr(portfolio, "active_projects", 0) or 0)
            late_tasks = int(getattr(kpi, "late_tasks", 0) or 0)
            cost_variance = float(getattr(kpi, "cost_variance", 0.0) or 0.0)
            return (
                ProjectDashboardHealthCardDescriptor(
                    id="schedule",
                    title="Schedule Health",
                    status_label="At Risk" if late_tasks > 0 else "On Track",
                    metric_value=_fmt_int(late_tasks),
                    metric_label="Late tasks",
                    supporting_text=f"{_fmt_int(active_projects)} active projects in view.",
                    meta_text="Portfolio schedule pressure across visible work.",
                    tone="danger" if late_tasks > 0 else "success",
                    route_id="project_management.scheduling",
                ),
                ProjectDashboardHealthCardDescriptor(
                    id="cost",
                    title="Cost Health",
                    status_label="Attention" if cost_variance > 0.0 else "Healthy",
                    metric_value=_fmt_float(cost_variance, 0),
                    metric_label="Cost variance",
                    supporting_text="Portfolio actual minus planned cost.",
                    meta_text="Positive variance indicates current overrun pressure.",
                    tone="danger" if cost_variance > 0.0 else "success",
                    route_id="project_management.financials",
                ),
                ProjectDashboardHealthCardDescriptor(
                    id="risk",
                    title="Risk Exposure",
                    status_label="Watch" if at_risk_projects > 0 else "Stable",
                    metric_value=_fmt_int(at_risk_projects),
                    metric_label="Projects at risk",
                    supporting_text=f"{_fmt_int(total_projects)} total projects in scope.",
                    meta_text="Cross-project delivery escalation load.",
                    tone="warning" if at_risk_projects > 0 else "success",
                    route_id="project_management.portfolio",
                ),
                ProjectDashboardHealthCardDescriptor(
                    id="resource",
                    title="Resource Health",
                    status_label="Overloaded" if overloads > 0 else "Balanced",
                    metric_value=_fmt_percent(peak_utilization, 0),
                    metric_label="Peak utilization",
                    supporting_text=f"{_fmt_int(overloads)} overloaded resource(s).",
                    meta_text=f"{_fmt_int(len(pending_approvals))} pending approvals in flow.",
                    tone="danger" if overloads > 0 else "success",
                    route_id="project_management.resources",
                ),
                self._build_baseline_variance_card(project_id),
            )

        late_tasks = int(getattr(kpi, "late_tasks", 0) or 0)
        critical_tasks = int(getattr(kpi, "critical_tasks", 0) or 0)
        cost_variance = float(getattr(kpi, "cost_variance", 0.0) or 0.0)
        schedule_tone = (
            "danger"
            if late_tasks > 0 or float(getattr(evm, "SPI", 1.0) or 1.0) < 0.95
            else "warning"
            if critical_tasks > 0 or float(getattr(evm, "SPI", 1.0) or 1.0) < 1.0
            else "success"
        )
        cost_tone = (
            "danger"
            if cost_variance > 0.0 or float(getattr(evm, "CPI", 1.0) or 1.0) < 0.95
            else "warning"
            if float(getattr(evm, "CPI", 1.0) or 1.0) < 1.0
            else "success"
        )
        risk_critical = int(getattr(summary, "critical_items", 0) or 0)
        risk_open = int(getattr(summary, "open_risks", 0) or 0)
        risk_tone = "danger" if risk_critical > 0 else "warning" if risk_open > 0 else "success"
        resource_tone = "danger" if overloads > 0 else "warning" if peak_utilization >= 90.0 else "success"
        return (
            ProjectDashboardHealthCardDescriptor(
                id="schedule",
                title="Schedule Health",
                status_label="Late" if late_tasks > 0 else "On Track",
                metric_value=f"SPI {_fmt_ratio(getattr(evm, 'SPI', None))}",
                metric_label="Schedule performance",
                supporting_text=(
                    f"Critical tasks {_fmt_int(critical_tasks)} | "
                    f"Late tasks {_fmt_int(late_tasks)}"
                ),
                meta_text="Critical-path and slip pressure across active activities.",
                tone=schedule_tone,
                route_id="project_management.scheduling",
            ),
            ProjectDashboardHealthCardDescriptor(
                id="cost",
                title="Cost Health",
                status_label="Overrun" if cost_variance > 0.0 else "Stable",
                metric_value=f"CPI {_fmt_ratio(getattr(evm, 'CPI', None))}",
                metric_label="Cost performance",
                supporting_text=(
                    f"Variance {_fmt_float(cost_variance, 0)} | "
                    f"VAC {_fmt_float(getattr(evm, 'VAC', 0.0), 0)}"
                ),
                meta_text="Cost and forecast pressure against the selected baseline.",
                tone=cost_tone,
                route_id="project_management.financials",
            ),
            ProjectDashboardHealthCardDescriptor(
                id="risk",
                title="Risk Exposure",
                status_label="Escalated" if risk_critical > 0 else "Managed",
                metric_value=_fmt_int(risk_critical),
                metric_label="Critical items",
                supporting_text=(
                    f"Open risks {_fmt_int(risk_open)} | "
                    f"Pending approvals {_fmt_int(len(pending_approvals))}"
                ),
                meta_text="Register pressure across risks, issues, and governed changes.",
                tone=risk_tone,
                route_id="project_management.risk",
            ),
            ProjectDashboardHealthCardDescriptor(
                id="resource",
                title="Resource Health",
                status_label="Overloaded" if overloads > 0 else "Balanced",
                metric_value=_fmt_percent(peak_utilization, 0),
                metric_label="Peak utilization",
                supporting_text=f"{_fmt_int(overloads)} overloaded resource(s).",
                meta_text="Load pressure across assigned delivery resources.",
                tone=resource_tone,
                route_id="project_management.resources",
            ),
            self._build_baseline_variance_card(project_id),
        )

    def _build_operational_tabs(
        self,
        tables: tuple[ProjectDashboardOperationalTableDescriptor, ...],
    ) -> tuple[ProjectDashboardOperationalTabDescriptor, ...]:
        return tuple(
            ProjectDashboardOperationalTabDescriptor(
                id=table.id,
                label=table.title,
                count=len(table.rows),
                route_id=(table.rows[0].route_id if table.rows else ""),
            )
            for table in tables
        )

    def _build_operational_tables(
        self,
        *,
        dashboard_data: Any,
        pending_approvals: tuple[Any, ...],
        selected_period_key: str,
        portfolio_mode: bool,
    ) -> tuple[ProjectDashboardOperationalTableDescriptor, ...]:
        if portfolio_mode:
            return (
                self._build_portfolio_health_table(dashboard_data),
                self._build_portfolio_delayed_table(
                    dashboard_data, selected_period_key=selected_period_key
                ),
                self._build_portfolio_budget_table(dashboard_data),
                self._build_resource_overloads_table(dashboard_data),
                self._build_pending_approvals_table(pending_approvals),
                self._build_milestones_table(dashboard_data),
            )
        return (
            self._build_delayed_tasks_table(dashboard_data),
            self._build_high_risks_table(dashboard_data),
            self._build_budget_variances_table(dashboard_data),
            self._build_resource_overloads_table(dashboard_data),
            self._build_pending_approvals_table(pending_approvals),
            self._build_milestones_table(dashboard_data),
        )

    def _build_delayed_tasks_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        rows = tuple(getattr(dashboard_data, "critical_watchlist", []) or [])
        return ProjectDashboardOperationalTableDescriptor(
            id="delayed_tasks",
            title="Delayed Tasks",
            subtitle="Critical-path and low-float tasks that need scheduling intervention.",
            empty_state="No delayed or critical-path tasks are active right now.",
            columns=(
                ProjectDashboardTableColumnDescriptor("taskName", "Activity", 3, 220, True),
                ProjectDashboardTableColumnDescriptor("owner", "Owner", 2, 140),
                ProjectDashboardTableColumnDescriptor("finish", "Finish", 1, 108, True),
                ProjectDashboardTableColumnDescriptor("float", "Float", 1, 90),
                ProjectDashboardTableColumnDescriptor("late", "Late", 1, 90),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 96, False, True, "status"
                ),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=row.task_id,
                    route_id="project_management.tasks",
                    state={"taskId": row.task_id, "projectId": getattr(dashboard_data.kpi, "project_id", "")},
                    values={
                        "taskName": row.task_name,
                        "owner": row.owner_name or "Unassigned",
                        "finish": _fmt_date(row.finish_date),
                        "float": f"{_fmt_int(row.total_float_days or 0)} d",
                        "late": f"{_fmt_int(row.late_by_days or 0)} d",
                        "statusLabel": row.status_label,
                    },
                )
                for row in rows
            ),
        )

    def _build_portfolio_delayed_table(
        self,
        dashboard_data: Any,
        *,
        selected_period_key: str,
    ) -> ProjectDashboardOperationalTableDescriptor:
        rows = list(tuple(getattr(dashboard_data, "upcoming_tasks", []) or []))
        cutoff = self._period_cutoff_date(selected_period_key)
        if cutoff is not None:
            rows = [
                row
                for row in rows
                if row.start_date is None or row.start_date >= cutoff
            ]
        return ProjectDashboardOperationalTableDescriptor(
            id="delayed_tasks",
            title="Delayed Tasks",
            subtitle="Cross-project upcoming and delayed work in the selected horizon.",
            empty_state="No cross-project delayed tasks are visible right now.",
            columns=(
                ProjectDashboardTableColumnDescriptor("taskName", "Task", 3, 220, True),
                ProjectDashboardTableColumnDescriptor("start", "Start", 1, 108, True),
                ProjectDashboardTableColumnDescriptor("finish", "Finish", 1, 108, True),
                ProjectDashboardTableColumnDescriptor("owner", "Owner", 2, 140),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 96, False, True, "status"
                ),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=row.task_id,
                    route_id="project_management.tasks",
                    state={"taskId": row.task_id, "projectId": getattr(row, "project_id", "")},
                    values={
                        "taskName": row.name,
                        "start": _fmt_date(row.start_date),
                        "finish": _fmt_date(row.end_date),
                        "owner": row.main_resource or "Unassigned",
                        "statusLabel": "Late" if row.is_late else "Tracked",
                    },
                )
                for row in rows
            ),
        )

    def _build_high_risks_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        project_id = str(getattr(dashboard_data.kpi, "project_id", "") or "")
        risk_rows: list[Any] = []
        if self._register_service is not None and project_id:
            try:
                risk_rows = sorted(
                    self._register_service.list_entries(
                        project_id=project_id,
                        entry_type=RegisterEntryType.RISK,
                    ),
                    key=lambda item: (
                        0 if item.severity == RegisterEntrySeverity.CRITICAL else 1,
                        0
                        if item.status == RegisterEntryStatus.OPEN
                        else 1,
                        item.due_date or date.max,
                        str(item.title or "").casefold(),
                    ),
                )
            except Exception:
                risk_rows = []
        return ProjectDashboardOperationalTableDescriptor(
            id="high_risks",
            title="High Risks",
            subtitle="Register risks that need active mitigation and escalation follow-through.",
            empty_state="No high-risk register entries are visible right now.",
            columns=(
                ProjectDashboardTableColumnDescriptor("title", "Risk", 3, 220, True),
                ProjectDashboardTableColumnDescriptor(
                    "severityLabel", "Severity", 0, 96, False, True, "status"
                ),
                ProjectDashboardTableColumnDescriptor("owner", "Owner", 2, 140),
                ProjectDashboardTableColumnDescriptor("dueDate", "Due", 1, 108, True),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 110, False, True, "status"
                ),
                ProjectDashboardTableColumnDescriptor("response", "Response", 3, 220),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=item.id,
                    route_id="project_management.risk",
                    state={"entryId": item.id, "projectId": item.project_id},
                    values={
                        "title": item.title,
                        "severityLabel": as_register_entry_severity(item.severity).value.title(),
                        "owner": item.owner_name or "Unassigned",
                        "dueDate": _fmt_date(item.due_date),
                        "statusLabel": as_register_entry_status(item.status).value.replace("_", " ").title(),
                        "response": item.response_plan or item.impact_summary or item.description or "",
                    },
                )
                for item in risk_rows
                if item.severity in (RegisterEntrySeverity.HIGH, RegisterEntrySeverity.CRITICAL)
                and item.status in (RegisterEntryStatus.OPEN, RegisterEntryStatus.IN_REVIEW)
            ),
        )

    def _build_portfolio_health_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        portfolio = getattr(dashboard_data, "portfolio", None)
        rankings = tuple(getattr(portfolio, "project_rankings", []) or [])
        return ProjectDashboardOperationalTableDescriptor(
            id="project_health",
            title="Projects at Risk",
            subtitle="Portfolio ranking by delivery pressure, late tasks, and cost variance.",
            empty_state="No project ranking data is available yet.",
            columns=(
                ProjectDashboardTableColumnDescriptor("projectName", "Project", 3, 220, True),
                ProjectDashboardTableColumnDescriptor(
                    "projectStatus", "Status", 0, 96, False, True, "status"
                ),
                ProjectDashboardTableColumnDescriptor("progress", "Progress", 1, 100),
                ProjectDashboardTableColumnDescriptor("late", "Late", 1, 90),
                ProjectDashboardTableColumnDescriptor("critical", "Critical", 1, 90),
                ProjectDashboardTableColumnDescriptor("riskScore", "Risk Score", 1, 100, True),
                ProjectDashboardTableColumnDescriptor("costVariance", "Cost Var.", 1, 110, True),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=row.project_id,
                    route_id="project_management.projects",
                    state={"projectId": row.project_id},
                    values={
                        "projectName": row.project_name,
                        "projectStatus": row.project_status,
                        "progress": _fmt_percent(row.progress_percent, 0),
                        "late": _fmt_int(row.late_tasks),
                        "critical": _fmt_int(row.critical_tasks),
                        "riskScore": _fmt_float(row.risk_score, 1),
                        "costVariance": _fmt_float(row.cost_variance, 0),
                    },
                )
                for row in rankings
            ),
        )

    def _build_budget_variances_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        sources = getattr(dashboard_data, "cost_sources", None)
        rows = tuple(getattr(sources, "rows", []) or []) if sources is not None else ()
        return ProjectDashboardOperationalTableDescriptor(
            id="budget_variances",
            title="Budget Variances",
            subtitle="Budget lines with actual, committed, and planned cost visibility.",
            empty_state="No budget variance rows are available yet.",
            columns=(
                ProjectDashboardTableColumnDescriptor("source", "Budget Line", 3, 200, True),
                ProjectDashboardTableColumnDescriptor("planned", "Planned", 1, 110, True),
                ProjectDashboardTableColumnDescriptor("actual", "Actual", 1, 110, True),
                ProjectDashboardTableColumnDescriptor("variance", "Variance", 1, 110, True),
                ProjectDashboardTableColumnDescriptor("committed", "Committed", 1, 110, True),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 96, False, True, "status"
                ),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=f"cost-source-{index}",
                    route_id="project_management.financials",
                    values={
                        "source": row.source_label,
                        "planned": _fmt_float(row.planned, 0),
                        "actual": _fmt_float(row.actual, 0),
                        "variance": _fmt_float(float(row.actual or 0.0) - float(row.planned or 0.0), 0),
                        "committed": _fmt_float(row.committed, 0),
                        "statusLabel": "Watch" if float(row.actual or 0.0) > float(row.planned or 0.0) else "Healthy",
                    },
                )
                for index, row in enumerate(rows, start=1)
            ),
        )

    def _build_portfolio_budget_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        portfolio = getattr(dashboard_data, "portfolio", None)
        rankings = tuple(getattr(portfolio, "project_rankings", []) or [])
        return ProjectDashboardOperationalTableDescriptor(
            id="budget_variances",
            title="Budget Variances",
            subtitle="Projects with the highest portfolio cost-variance exposure.",
            empty_state="No portfolio budget-variance rows are available yet.",
            columns=(
                ProjectDashboardTableColumnDescriptor("projectName", "Project", 3, 220, True),
                ProjectDashboardTableColumnDescriptor(
                    "projectStatus", "Status", 0, 96, False, True, "status"
                ),
                ProjectDashboardTableColumnDescriptor("costVariance", "Cost Var.", 1, 110, True),
                ProjectDashboardTableColumnDescriptor("late", "Late", 1, 90, True),
                ProjectDashboardTableColumnDescriptor("critical", "Critical", 1, 90, True),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=row.project_id,
                    route_id="project_management.financials",
                    state={"projectId": row.project_id},
                    values={
                        "projectName": row.project_name,
                        "projectStatus": row.project_status,
                        "costVariance": _fmt_float(row.cost_variance, 0),
                        "late": _fmt_int(row.late_tasks),
                        "critical": _fmt_int(row.critical_tasks),
                    },
                )
                for row in rankings
            ),
        )

    def _build_resource_overloads_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
        return ProjectDashboardOperationalTableDescriptor(
            id="resource_overloads",
            title="Resource Overloads",
            subtitle="Utilization and overload hotspots across assigned delivery resources.",
            empty_state="No resource loading data is available yet.",
            columns=(
                ProjectDashboardTableColumnDescriptor("resourceName", "Resource", 3, 180, True),
                ProjectDashboardTableColumnDescriptor(
                    "utilization", "Utilization", 2, 180, False, True, "progress"
                ),
                ProjectDashboardTableColumnDescriptor("allocation", "Allocation", 1, 100),
                ProjectDashboardTableColumnDescriptor("capacity", "Capacity", 1, 100),
                ProjectDashboardTableColumnDescriptor("tasks", "Tasks", 1, 80, True),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 96, False, True, "status"
                ),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=row.resource_id,
                    route_id="project_management.resources",
                    state={"resourceId": row.resource_id},
                    values={
                        "resourceName": row.resource_name,
                        "utilization": {
                            "value": min(
                                max(
                                    float(
                                        getattr(
                                            row,
                                            "utilization_percent",
                                            getattr(row, "total_allocation_percent", 0.0),
                                        )
                                        or 0.0
                                    )
                                    / 100.0,
                                    0.0,
                                ),
                                2.0,
                            ),
                            "label": _fmt_percent(
                                getattr(
                                    row,
                                    "utilization_percent",
                                    getattr(row, "total_allocation_percent", 0.0),
                                ),
                                0,
                            ),
                        },
                        "allocation": _fmt_percent(row.total_allocation_percent, 0),
                        "capacity": _fmt_percent(row.capacity_percent, 0),
                        "tasks": _fmt_int(row.tasks_count),
                        "statusLabel": (
                            "Overloaded"
                            if float(
                                getattr(
                                    row,
                                    "utilization_percent",
                                    getattr(row, "total_allocation_percent", 0.0),
                                )
                                or 0.0
                            )
                            > 100.0
                            else "Balanced"
                        ),
                    },
                )
                for row in rows
            ),
        )

    def _build_pending_approvals_table(
        self, pending_approvals: tuple[Any, ...]
    ) -> ProjectDashboardOperationalTableDescriptor:
        from src.api.desktop.platform._approval_labels import (
            approval_context_label,
            approval_display_label,
            approval_module_label,
        )

        return ProjectDashboardOperationalTableDescriptor(
            id="pending_approvals",
            title="Pending Approvals",
            subtitle="Governed changes waiting for decision or application.",
            empty_state="No pending approvals are active right now.",
            columns=(
                ProjectDashboardTableColumnDescriptor("request", "Request", 3, 240, True),
                ProjectDashboardTableColumnDescriptor("module", "Module", 1, 120),
                ProjectDashboardTableColumnDescriptor("context", "Context", 2, 180),
                ProjectDashboardTableColumnDescriptor("requestedBy", "Requested By", 1, 120),
                ProjectDashboardTableColumnDescriptor("requestedAt", "Requested At", 1, 132, True),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 96, False, True, "status"
                ),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=request.id,
                    route_id="platform.control",
                    state={"requestId": request.id, "projectId": request.project_id or ""},
                    values={
                        "request": approval_display_label(request),
                        "module": approval_module_label(request),
                        "context": approval_context_label(request),
                        "requestedBy": request.requested_by_username or "Unknown",
                        "requestedAt": _fmt_utc_datetime(
                            _coerce_utc_datetime(getattr(request, "requested_at", None))
                        ),
                        "statusLabel": str(
                            getattr(
                                getattr(request, "status", ApprovalStatus.PENDING),
                                "value",
                                getattr(request, "status", ApprovalStatus.PENDING),
                            )
                        ).replace("_", " ").title(),
                    },
                )
                for request in pending_approvals
            ),
        )

    def _build_milestones_table(
        self, dashboard_data: Any
    ) -> ProjectDashboardOperationalTableDescriptor:
        rows = tuple(getattr(dashboard_data, "milestone_health", []) or [])
        return ProjectDashboardOperationalTableDescriptor(
            id="milestones",
            title="Milestone Health",
            subtitle="Delivery checkpoints and schedule slips that require planning attention.",
            empty_state="No milestone health rows are available yet.",
            columns=(
                ProjectDashboardTableColumnDescriptor("milestone", "Milestone", 3, 220, True),
                ProjectDashboardTableColumnDescriptor("owner", "Owner", 2, 140),
                ProjectDashboardTableColumnDescriptor("target", "Target", 1, 108, True),
                ProjectDashboardTableColumnDescriptor("slip", "Slip", 1, 90, True),
                ProjectDashboardTableColumnDescriptor(
                    "statusLabel", "Status", 0, 96, False, True, "status"
                ),
            ),
            rows=tuple(
                ProjectDashboardTableRowDescriptor(
                    id=row.task_id,
                    route_id="project_management.scheduling",
                    state={"taskId": row.task_id, "projectId": getattr(dashboard_data.kpi, "project_id", "")},
                    values={
                        "milestone": row.task_name,
                        "owner": row.owner_name or "Unassigned",
                        "target": _fmt_date(row.target_date),
                        "slip": f"{_fmt_int(row.slip_days or 0)} d",
                        "statusLabel": row.status_label,
                    },
                )
                for row in rows
            ),
        )

    def _build_activity_feed(
        self,
        *,
        project_id: str | None,
        selected_period_key: str,
        portfolio_mode: bool,
    ) -> ProjectDashboardActivityFeedDescriptor:
        if self._collaboration_service is None:
            return ProjectDashboardActivityFeedDescriptor(
                title="Recent Activity",
                subtitle="Activity stream is not connected for this dashboard preview.",
                empty_state="No collaboration or workflow activity is available yet.",
            )
        cutoff = self._period_cutoff_datetime(selected_period_key)
        try:
            snapshot = self._collaboration_service.list_workspace_snapshot(limit=120)
        except Exception:
            return ProjectDashboardActivityFeedDescriptor(
                title="Recent Activity",
                subtitle="Activity feed is unavailable for the current session.",
                empty_state="No collaboration or workflow activity is available yet.",
            )
        items: list[tuple[datetime, ProjectDashboardActivityItemDescriptor]] = []
        for note in getattr(snapshot, "notifications", []) or []:
            if project_id and str(getattr(note, "project_id", "") or "") != project_id:
                continue
            created_at = _coerce_utc_datetime(getattr(note, "created_at", None))
            if cutoff is not None and created_at is not None and created_at < cutoff:
                continue
            route_id = "platform.control" if str(getattr(note, "entity_type", "") or "") == "approval_request" else "project_management.collaboration"
            items.append(
                (
                    created_at or datetime.now(timezone.utc),
                    ProjectDashboardActivityItemDescriptor(
                        id=f"note-{getattr(note, 'entity_id', '')}-{len(items)}",
                        title=str(getattr(note, "headline", "") or ""),
                        status_label=str(getattr(note, "notification_type", "") or "").replace("_", " ").title(),
                        meta_text=(
                            f"{getattr(note, 'project_name', '') or 'Project'} • "
                            f"{getattr(note, 'actor_username', '') or 'system'} • "
                            f"{_fmt_utc_datetime(created_at)}"
                        ).strip(" •"),
                        route_id=route_id,
                        state={
                            "entityId": getattr(note, "entity_id", ""),
                            "projectId": getattr(note, "project_id", "") or "",
                            "entityType": getattr(note, "entity_type", ""),
                        },
                    ),
                )
            )
        for activity in getattr(snapshot, "recent_activity", []) or []:
            if project_id and str(getattr(activity, "project_id", "") or "") != project_id:
                continue
            created_at = _coerce_utc_datetime(getattr(activity, "created_at", None))
            if cutoff is not None and created_at is not None and created_at < cutoff:
                continue
            items.append(
                (
                    created_at or datetime.now(timezone.utc),
                    ProjectDashboardActivityItemDescriptor(
                        id=f"comment-{getattr(activity, 'comment_id', '')}",
                        title=f"{getattr(activity, 'task_name', '') or 'Task'} update",
                        status_label="Mention" if bool(getattr(activity, "unread", False)) else "Comment",
                        meta_text=(
                            f"{getattr(activity, 'project_name', '') or 'Project'} • "
                            f"{getattr(activity, 'author_username', '') or 'unknown'} • "
                            f"{_fmt_utc_datetime(created_at)}"
                        ).strip(" •"),
                        route_id="project_management.tasks",
                        state={
                            "taskId": getattr(activity, "task_id", ""),
                            "projectId": getattr(activity, "project_id", ""),
                            "commentId": getattr(activity, "comment_id", ""),
                        },
                    ),
                )
            )
        items.sort(key=lambda item: item[0], reverse=True)
        return ProjectDashboardActivityFeedDescriptor(
            title="Recent Activity",
            subtitle=(
                "Portfolio workflow notifications, approvals, and task updates."
                if portfolio_mode
                else "Latest project workflow notifications, approvals, and task updates."
            ),
            empty_state="No recent dashboard activity is available in the selected period.",
            items=tuple(item for _, item in items[:24]),
        )

    def _list_pending_approvals(
        self, *, project_id: str | None
    ) -> tuple[Any, ...]:
        if self._approval_service is None:
            return ()
        try:
            return tuple(
                self._approval_service.list_pending(project_id=project_id, limit=120)
            )
        except Exception:
            return ()

    def _build_panels_from_dashboard_data(
        self,
        *,
        dashboard_data: Any,
        baseline_label: str,
        selected_baseline_id: str,
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
            self._build_baseline_variance_panel(
                selected_baseline_id=selected_baseline_id,
                portfolio_mode=portfolio_mode,
            ),
            self._build_resource_overload_panel(
                dashboard_data=dashboard_data,
                portfolio_mode=portfolio_mode,
            ),
            self._build_reports_panel(portfolio_mode=portfolio_mode),
        )

    def _build_charts_from_dashboard_data(
        self,
        *,
        dashboard_data: Any,
        selected_period_key: str,
        portfolio_mode: bool,
    ) -> tuple[ProjectDashboardChartDescriptor, ...]:
        if portfolio_mode:
            return (
                self._build_portfolio_status_chart(dashboard_data=dashboard_data),
                self._build_portfolio_cost_chart(dashboard_data=dashboard_data),
                self._build_resource_chart(
                    dashboard_data=dashboard_data,
                    portfolio_mode=True,
                ),
            )
        return (
            self._build_schedule_trend_chart(
                dashboard_data=dashboard_data,
                selected_period_key=selected_period_key,
            ),
            self._build_cost_trend_chart(
                dashboard_data=dashboard_data,
                selected_period_key=selected_period_key,
            ),
            self._build_resource_chart(
                dashboard_data=dashboard_data,
                portfolio_mode=False,
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
        sections.append(self._build_reports_section())
        return tuple(sections)

    def _build_reports_section(self) -> ProjectDashboardSectionDescriptor:
        common_reports = (
            ("kpi_summary", "Project KPIs", "project_management.dashboard", "Key metrics: task completion, SPI, CPI, and late count."),
            ("evm_summary", "Earned Value Summary", "project_management.financials", "BCWS, BCWP, ACWP, SPI, CPI, and VAC per period."),
            ("resource_utilization", "Resource Utilization", "project_management.resources", "Allocation %, peak load, and overload indicators per resource."),
            ("baseline_variance", "Baseline Variance", "project_management.scheduling", "Start and finish drift vs. the approved baseline per task."),
            ("risk_register", "Risk Register Summary", "project_management.risk", "Open risks, issues, and change requests by severity and status."),
        )
        return ProjectDashboardSectionDescriptor(
            title="Reports",
            subtitle="Quick links to common project reports. Open the workspace to run or export each report.",
            empty_state="No reports are configured for this project.",
            items=tuple(
                ProjectDashboardSectionItemDescriptor(
                    id=report_id,
                    title=title,
                    status_label="Available",
                    subtitle=description,
                    meta_text="Open workspace →",
                    state={"routeId": route_id},
                )
                for report_id, title, route_id, description in common_reports
            ),
        )

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

    def _build_baseline_variance_panel(
        self,
        *,
        selected_baseline_id: str,
        portfolio_mode: bool,
    ) -> ProjectDashboardPanelDescriptor:
        if portfolio_mode:
            return ProjectDashboardPanelDescriptor(
                title="Baseline Variance",
                subtitle="Task schedule and cost drift between baselines.",
                empty_state="Baseline variance records are project-scoped and not rolled up in portfolio mode.",
            )
        if not selected_baseline_id or self._baseline_service is None:
            return ProjectDashboardPanelDescriptor(
                title="Baseline Variance",
                subtitle="Task schedule and cost drift between baselines.",
                empty_state="Select a baseline to view schedule and cost variance records.",
            )
        try:
            records = self._baseline_service.list_variance_records(selected_baseline_id)
        except Exception:
            records = []
        if not records:
            return ProjectDashboardPanelDescriptor(
                title="Baseline Variance",
                subtitle="Task schedule and cost drift between baselines.",
                empty_state="No variance records found for the selected baseline.",
            )
        sorted_records = sorted(
            records,
            key=lambda r: abs(r.start_variance_days or 0) + abs(r.finish_variance_days or 0),
            reverse=True,
        )[:8]
        return ProjectDashboardPanelDescriptor(
            title="Baseline Variance",
            subtitle=f"Top {len(sorted_records)} task(s) with schedule or cost drift.",
            rows=tuple(
                ProjectDashboardPanelRowDescriptor(
                    label=str(r.task_name or r.task_id or "Task"),
                    value=f"{r.start_variance_days:+d}d / {r.finish_variance_days:+d}d",
                    supporting_text=(
                        f"Cost delta: {_fmt_float(r.cost_variance, 0)}"
                        if r.cost_variance != 0.0
                        else "No cost drift"
                    ),
                    tone=(
                        "danger"
                        if abs(r.finish_variance_days or 0) > 5
                        else "warning"
                        if abs(r.finish_variance_days or 0) > 0
                        else "default"
                    ),
                )
                for r in sorted_records
            ),
        )

    def _build_resource_overload_panel(
        self,
        *,
        dashboard_data: Any,
        portfolio_mode: bool,
    ) -> ProjectDashboardPanelDescriptor:
        rows = tuple(getattr(dashboard_data, "resource_load", []) or [])
        overloaded = [
            r for r in rows
            if float(
                getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0
            ) > 100.0
        ]
        at_risk = [
            r for r in rows
            if 90.0 <= float(
                getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0
            ) <= 100.0
        ]
        if not rows:
            return ProjectDashboardPanelDescriptor(
                title="Resource Overloads",
                subtitle="Resources that exceed capacity across assigned activities.",
                empty_state="No resource loading data is available yet.",
            )
        if not overloaded and not at_risk:
            return ProjectDashboardPanelDescriptor(
                title="Resource Overloads",
                subtitle="All resources are within capacity.",
                metrics=(
                    ProjectDashboardMetricDescriptor(
                        "Resources", _fmt_int(len(rows)), "In scope"
                    ),
                    ProjectDashboardMetricDescriptor(
                        "Overloaded", "0", "Above 100% capacity"
                    ),
                    ProjectDashboardMetricDescriptor(
                        "At Risk", "0", "90–100% utilization"
                    ),
                ),
            )
        display = (overloaded + at_risk)[:8]
        return ProjectDashboardPanelDescriptor(
            title="Resource Overloads",
            subtitle=(
                f"{_fmt_int(len(overloaded))} overloaded, {_fmt_int(len(at_risk))} near-capacity."
            ),
            metrics=(
                ProjectDashboardMetricDescriptor(
                    "Resources", _fmt_int(len(rows)), "In scope"
                ),
                ProjectDashboardMetricDescriptor(
                    "Overloaded", _fmt_int(len(overloaded)), "Above 100% capacity"
                ),
                ProjectDashboardMetricDescriptor(
                    "At Risk", _fmt_int(len(at_risk)), "90–100% utilization"
                ),
            ),
            rows=tuple(
                ProjectDashboardPanelRowDescriptor(
                    label=str(getattr(r, "resource_name", "") or "Resource"),
                    value=_fmt_percent(
                        getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)), 0
                    ),
                    supporting_text=f"Capacity: {_fmt_percent(getattr(r, 'capacity_percent', 100.0), 0)}",
                    tone=(
                        "danger"
                        if float(
                            getattr(r, "utilization_percent", getattr(r, "total_allocation_percent", 0.0)) or 0.0
                        ) > 100.0
                        else "warning"
                    ),
                )
                for r in display
            ),
        )

    @staticmethod
    def _build_reports_panel(
        *,
        portfolio_mode: bool,
    ) -> ProjectDashboardPanelDescriptor:
        if portfolio_mode:
            return ProjectDashboardPanelDescriptor(
                title="Available Reports",
                subtitle="Report formats available for portfolio export.",
                rows=(
                    ProjectDashboardPanelRowDescriptor(
                        "Portfolio Summary PDF",
                        "Export",
                        "Cross-project delivery summary report.",
                    ),
                    ProjectDashboardPanelRowDescriptor(
                        "Resource Utilization Excel",
                        "Export",
                        "Portfolio resource loading and capacity data.",
                    ),
                ),
            )
        return ProjectDashboardPanelDescriptor(
            title="Available Reports",
            subtitle="Report formats available for this project.",
            rows=(
                ProjectDashboardPanelRowDescriptor(
                    "Gantt Chart (PNG)",
                    "Export",
                    "Schedule bar chart with critical path.",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "EVM Curve (PNG)",
                    "Export",
                    "Planned value vs earned value vs actual cost trend.",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "Full Project Report (Excel)",
                    "Export",
                    "Tasks, assignments, costs, and baseline in one workbook.",
                ),
                ProjectDashboardPanelRowDescriptor(
                    "Project Status Report (PDF)",
                    "Export",
                    "Formatted delivery status report for stakeholders.",
                ),
            ),
        )

    def _build_portfolio_status_chart(
        self,
        *,
        dashboard_data: Any,
    ) -> ProjectDashboardChartDescriptor:
        portfolio = getattr(dashboard_data, "portfolio", None)
        rollup = tuple(getattr(portfolio, "status_rollup", []) or []) if portfolio is not None else ()
        return ProjectDashboardChartDescriptor(
            title="Portfolio Status",
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

    def _build_portfolio_cost_chart(
        self,
        *,
        dashboard_data: Any,
    ) -> ProjectDashboardChartDescriptor:
        portfolio = getattr(dashboard_data, "portfolio", None)
        rankings = tuple(getattr(portfolio, "project_rankings", []) or [])
        return ProjectDashboardChartDescriptor(
            title="Cost Pressure",
            subtitle="Projects with the highest variance pressure.",
            chart_type="bar",
            empty_state="No project cost-pressure rows are available yet.",
            points=tuple(
                ProjectDashboardChartPointDescriptor(
                    label=row.project_name,
                    value=float(abs(row.cost_variance or 0.0)),
                    value_label=_fmt_float(row.cost_variance, 0),
                    supporting_text=(
                        f"Late {_fmt_int(row.late_tasks)} | Critical {_fmt_int(row.critical_tasks)}"
                    ),
                    tone="danger" if float(row.cost_variance or 0.0) > 0.0 else "accent",
                )
                for row in rankings[:8]
            ),
        )

    def _build_schedule_trend_chart(
        self,
        *,
        dashboard_data: Any,
        selected_period_key: str,
    ) -> ProjectDashboardChartDescriptor:
        series = self._filtered_evm_series(
            project_id=str(getattr(dashboard_data.kpi, "project_id", "") or ""),
            baseline_id=getattr(getattr(dashboard_data, "evm", None), "baseline_id", None),
            selected_period_key=selected_period_key,
        )
        if series:
            series_length = len(series)
            return ProjectDashboardChartDescriptor(
                title="Schedule Trend",
                subtitle="Earned value against planned value across the selected period.",
                chart_type="line",
                points=tuple(
                    ProjectDashboardChartPointDescriptor(
                        label=_fmt_period_axis_label(
                            point.period_end,
                            selected_period_key=selected_period_key,
                            series_length=series_length,
                        ),
                        value=float(point.EV or 0.0),
                        value_label=_fmt_float(point.EV, 0),
                        supporting_text=point.period_end.strftime("%Y-%m-%d"),
                        target_value=float(point.PV or 0.0),
                        tone="danger" if float(point.SPI or 0.0) < 0.95 else "accent",
                    )
                    for point in series
                ),
            )
        return self._build_burndown_fallback_chart(dashboard_data)

    def _build_cost_trend_chart(
        self,
        *,
        dashboard_data: Any,
        selected_period_key: str,
    ) -> ProjectDashboardChartDescriptor:
        series = self._filtered_evm_series(
            project_id=str(getattr(dashboard_data.kpi, "project_id", "") or ""),
            baseline_id=getattr(getattr(dashboard_data, "evm", None), "baseline_id", None),
            selected_period_key=selected_period_key,
        )
        if series:
            series_length = len(series)
            return ProjectDashboardChartDescriptor(
                title="Cost Trend",
                subtitle="Actual cost against earned value across the selected period.",
                chart_type="line",
                points=tuple(
                    ProjectDashboardChartPointDescriptor(
                        label=_fmt_period_axis_label(
                            point.period_end,
                            selected_period_key=selected_period_key,
                            series_length=series_length,
                        ),
                        value=float(point.AC or 0.0),
                        value_label=_fmt_float(point.AC, 0),
                        supporting_text=point.period_end.strftime("%Y-%m-%d"),
                        target_value=float(point.EV or 0.0),
                        tone="danger" if float(point.AC or 0.0) > float(point.EV or 0.0) else "accent",
                    )
                    for point in series
                ),
            )
        sources = getattr(dashboard_data, "cost_sources", None)
        source_rows = tuple(getattr(sources, "rows", []) or []) if sources is not None else ()
        return ProjectDashboardChartDescriptor(
            title="Cost Trend",
            subtitle="Actual cost against planned budget lines.",
            chart_type="bar",
            empty_state="No cost-trend data is available yet for this project.",
            points=tuple(
                ProjectDashboardChartPointDescriptor(
                    label=row.source_label,
                    value=float(row.actual or 0.0),
                    value_label=_fmt_float(row.actual, 0),
                    supporting_text=f"Planned {_fmt_float(row.planned, 0)}",
                    target_value=float(row.planned or 0.0),
                    tone="danger" if float(row.actual or 0.0) > float(row.planned or 0.0) else "accent",
                )
                for row in source_rows[:8]
            ),
        )

    def _build_burndown_fallback_chart(
        self,
        dashboard_data: Any,
    ) -> ProjectDashboardChartDescriptor:
        points = tuple(getattr(dashboard_data, "burndown", []) or [])
        if not points:
            return ProjectDashboardChartDescriptor(
                title="Schedule Trend",
                subtitle="Remaining tasks over time against the ideal trend.",
                chart_type="line",
                empty_state="No schedule-trend data is available yet for this project.",
            )
        start_value = float(getattr(points[0], "remaining_tasks", 0) or 0)
        denominator = max(len(points) - 1, 1)
        return ProjectDashboardChartDescriptor(
            title="Schedule Trend",
            subtitle="Remaining tasks over time against the ideal trend.",
            chart_type="line",
            points=tuple(
                ProjectDashboardChartPointDescriptor(
                    label=point.day.strftime("%d %b"),
                    value=float(point.remaining_tasks or 0),
                    value_label=_fmt_int(point.remaining_tasks),
                    supporting_text=point.day.strftime("%Y-%m-%d"),
                    target_value=(start_value * (1.0 - (index / denominator))) if len(points) > 1 else 0.0,
                    tone="accent",
                )
                for index, point in enumerate(points)
            ),
        )

    def _filtered_evm_series(
        self,
        *,
        project_id: str,
        baseline_id: str | None,
        selected_period_key: str,
    ) -> tuple[Any, ...]:
        if self._reporting_service is None or not project_id:
            return ()
        try:
            get_series = getattr(self._reporting_service, "get_evm_series", None)
            if not callable(get_series):
                return ()
            series = tuple(
                get_series(project_id, baseline_id=baseline_id or None, as_of=date.today())
                or ()
            )
        except Exception:
            return ()
        cutoff = self._period_cutoff_date(selected_period_key)
        if cutoff is None:
            return series
        filtered = tuple(point for point in series if getattr(point, "period_end", cutoff) >= cutoff)
        return filtered or series[-6:]

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
    reporting_service: ReportingService | None = None,
    register_service: RegisterService | None = None,
    collaboration_service: CollaborationService | None = None,
    approval_service: ApprovalService | None = None,
) -> ProjectManagementDashboardDesktopApi:
    return ProjectManagementDashboardDesktopApi(
        project_service=project_service,
        dashboard_service=dashboard_service,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
        register_service=register_service,
        collaboration_service=collaboration_service,
        approval_service=approval_service,
    )


__all__ = [
    "ProjectDashboardActivityFeedDescriptor",
    "ProjectDashboardActivityItemDescriptor",
    "ProjectDashboardChartDescriptor",
    "ProjectDashboardChartPointDescriptor",
    "ProjectDashboardHealthCardDescriptor",
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectDashboardOperationalTabDescriptor",
    "ProjectDashboardOperationalTableDescriptor",
    "ProjectDashboardPanelDescriptor",
    "ProjectDashboardPanelRowDescriptor",
    "ProjectDashboardSectionDescriptor",
    "ProjectDashboardSectionItemDescriptor",
    "ProjectDashboardSelectorOptionDescriptor",
    "ProjectDashboardSnapshotDescriptor",
    "ProjectDashboardTableColumnDescriptor",
    "ProjectDashboardTableRowDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
]
