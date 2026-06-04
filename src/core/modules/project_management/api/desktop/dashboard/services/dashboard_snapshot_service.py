"""Dashboard snapshot assembly and orchestration service."""

from __future__ import annotations
from typing import Any

from src.core.modules.project_management.application.dashboard import PORTFOLIO_SCOPE_ID
from src.core.modules.project_management.api.desktop.dashboard.models.snapshot import (
    ProjectDashboardSelectorOptionDescriptor,
    ProjectDashboardSnapshotDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.sections import (
    ProjectDashboardSectionDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.selector_builder import (
    baseline_label_for_id,
    build_baseline_options,
    build_period_options,
    build_project_options,
    build_view_options,
    project_label_for_id,
    resolve_baseline_id,
    resolve_period_key,
    resolve_project_id,
    resolve_view_key,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.overview_builder import (
    build_contextual_overview,
    build_empty_overview,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.health_card_builder import (
    build_health_cards,
    build_preview_health_cards,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.operational_table_builder import (
    build_operational_tables,
    build_operational_tabs,
    build_preview_operational_tables,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.activity_feed_builder import (
    build_activity_feed,
    build_preview_activity_feed,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.chart_builder import (
    build_charts_from_dashboard_data,
    build_preview_charts,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.panel_builder import (
    build_panels_from_dashboard_data,
    build_preview_panels,
)
from src.core.modules.project_management.api.desktop.dashboard.builders.section_builder import (
    build_sections_from_dashboard_data,
)


class DashboardSnapshotService:
    """Assembles the complete dashboard snapshot descriptor."""

    def __init__(
        self,
        *,
        project_service=None,
        dashboard_service=None,
        baseline_service=None,
        reporting_service=None,
        register_service=None,
        collaboration_service=None,
        approval_service=None,
    ) -> None:
        self._project_service = project_service
        self._dashboard_service = dashboard_service
        self._baseline_service = baseline_service
        self._reporting_service = reporting_service
        self._register_service = register_service
        self._collaboration_service = collaboration_service
        self._approval_service = approval_service

    def build_snapshot(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
        period_key: str | None = None,
        view_key: str | None = None,
    ) -> ProjectDashboardSnapshotDescriptor:
        project_options = build_project_options(self._project_service)
        selected_project_id = resolve_project_id(project_id, project_options)
        baseline_options = build_baseline_options(selected_project_id, self._baseline_service)
        selected_baseline_id = resolve_baseline_id(baseline_id, baseline_options)
        period_options = build_period_options()
        selected_period_key = resolve_period_key(period_key, period_options)
        view_options = build_view_options()
        selected_view_key = resolve_view_key(view_key, view_options)

        _selectors = dict(
            project_options=project_options,
            selected_project_id=selected_project_id,
            baseline_options=baseline_options,
            selected_baseline_id=selected_baseline_id,
            period_options=period_options,
            selected_period_key=selected_period_key,
            view_options=view_options,
            selected_view_key=selected_view_key,
        )

        if self._dashboard_service is None:
            preview_tables = build_preview_operational_tables()
            return ProjectDashboardSnapshotDescriptor(
                overview=build_empty_overview(),
                **_selectors,
                health_cards=build_preview_health_cards(),
                operational_tabs=build_operational_tabs(preview_tables),
                operational_tables=preview_tables,
                activity_feed=build_preview_activity_feed(),
                panels=build_preview_panels(),
                charts=build_preview_charts(),
                sections=(ProjectDashboardSectionDescriptor(
                    title="Dashboard Preview",
                    subtitle="Dashboard sections appear here once the PM dashboard desktop API is connected.",
                    empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
                ),),
                empty_state="Project-management dashboard desktop API is not connected in this QML preview.",
            )

        portfolio_mode = selected_project_id == PORTFOLIO_SCOPE_ID

        if portfolio_mode:
            dashboard_data = self._dashboard_service.get_portfolio_data()
            pending_approvals = self._list_pending_approvals(project_id=None)
            operational_tables = build_operational_tables(dashboard_data=dashboard_data, pending_approvals=pending_approvals, selected_period_key=selected_period_key, portfolio_mode=True, register_service=self._register_service)
            return ProjectDashboardSnapshotDescriptor(
                overview=build_contextual_overview(project_name="Portfolio Overview", dashboard_data=dashboard_data, pending_approval_count=len(pending_approvals), selected_view_key=selected_view_key, portfolio_mode=True),
                **_selectors,
                health_cards=build_health_cards(dashboard_data=dashboard_data, pending_approvals=pending_approvals, portfolio_mode=True, project_id=None, baseline_service=self._baseline_service),
                operational_tabs=build_operational_tabs(operational_tables),
                operational_tables=operational_tables,
                activity_feed=build_activity_feed(project_id=None, selected_period_key=selected_period_key, portfolio_mode=True, collaboration_service=self._collaboration_service),
                panels=build_panels_from_dashboard_data(dashboard_data=dashboard_data, baseline_label="Portfolio view", selected_baseline_id="", portfolio_mode=True, baseline_service=self._baseline_service),
                charts=build_charts_from_dashboard_data(dashboard_data=dashboard_data, selected_period_key=selected_period_key, portfolio_mode=True, reporting_service=self._reporting_service),
                sections=build_sections_from_dashboard_data(dashboard_data=dashboard_data, portfolio_mode=True),
                empty_state=(
                    "No project dashboard data is available yet."
                    if not getattr(dashboard_data, "portfolio", None) or not getattr(dashboard_data.portfolio, "projects_total", 0)
                    else ""
                ),
            )

        project_label = project_label_for_id(selected_project_id, project_options)
        baseline_label = baseline_label_for_id(selected_baseline_id, baseline_options)
        dashboard_data = self._dashboard_service.get_dashboard_data(selected_project_id, baseline_id=selected_baseline_id or None)
        pending_approvals = self._list_pending_approvals(project_id=selected_project_id)
        operational_tables = build_operational_tables(dashboard_data=dashboard_data, pending_approvals=pending_approvals, selected_period_key=selected_period_key, portfolio_mode=False, register_service=self._register_service)
        return ProjectDashboardSnapshotDescriptor(
            overview=build_contextual_overview(project_name=project_label, dashboard_data=dashboard_data, pending_approval_count=len(pending_approvals), selected_view_key=selected_view_key, portfolio_mode=False),
            **_selectors,
            health_cards=build_health_cards(dashboard_data=dashboard_data, pending_approvals=pending_approvals, portfolio_mode=False, project_id=selected_project_id, baseline_service=self._baseline_service),
            operational_tabs=build_operational_tabs(operational_tables),
            operational_tables=operational_tables,
            activity_feed=build_activity_feed(project_id=selected_project_id, selected_period_key=selected_period_key, portfolio_mode=False, collaboration_service=self._collaboration_service),
            panels=build_panels_from_dashboard_data(dashboard_data=dashboard_data, baseline_label=baseline_label, selected_baseline_id=selected_baseline_id, portfolio_mode=False, baseline_service=self._baseline_service),
            charts=build_charts_from_dashboard_data(dashboard_data=dashboard_data, selected_period_key=selected_period_key, portfolio_mode=False, reporting_service=self._reporting_service),
            sections=build_sections_from_dashboard_data(dashboard_data=dashboard_data, portfolio_mode=False),
            empty_state="Add tasks, baselines, and resource assignments to populate the dashboard sections.",
        )

    def _list_pending_approvals(self, *, project_id: str | None) -> tuple[Any, ...]:
        if self._approval_service is None:
            return ()
        try:
            return tuple(self._approval_service.list_pending(project_id=project_id, limit=120))
        except Exception:
            return ()


__all__ = ["DashboardSnapshotService"]
