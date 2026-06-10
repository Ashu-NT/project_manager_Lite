from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementDashboardDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardWorkspaceViewModel,
)

from .activity_feed_mapper import to_activity_feed
from .chart_mapper import to_charts
from .health_card_mapper import to_health_cards, to_operational_tabs
from .operational_table_mapper import to_operational_tables
from .option_mapper import to_selector_options
from .overview_mapper import to_overview_view_model
from .panel_mapper import to_panels
from .section_mapper import to_sections


def build_workspace_state(
    desktop_api: ProjectManagementDashboardDesktopApi,
    *,
    project_id: str | None = None,
    baseline_id: str | None = None,
    period_key: str | None = None,
    view_key: str | None = None,
) -> ProjectDashboardWorkspaceViewModel:
    snapshot = desktop_api.build_snapshot(
        project_id=project_id,
        baseline_id=baseline_id,
        period_key=period_key,
        view_key=view_key,
    )
    return ProjectDashboardWorkspaceViewModel(
        overview=to_overview_view_model(snapshot.overview),
        project_options=to_selector_options(snapshot.project_options),
        selected_project_id=snapshot.selected_project_id,
        baseline_options=to_selector_options(snapshot.baseline_options),
        selected_baseline_id=snapshot.selected_baseline_id,
        period_options=to_selector_options(snapshot.period_options),
        selected_period_key=snapshot.selected_period_key,
        view_options=to_selector_options(snapshot.view_options),
        selected_view_key=snapshot.selected_view_key,
        health_cards=to_health_cards(snapshot.health_cards),
        operational_tabs=to_operational_tabs(snapshot.operational_tabs),
        operational_tables=to_operational_tables(snapshot.operational_tables),
        activity_feed=to_activity_feed(snapshot.activity_feed),
        panels=to_panels(snapshot.panels),
        charts=to_charts(snapshot.charts),
        sections=to_sections(snapshot.sections),
        empty_state=snapshot.empty_state,
    )
