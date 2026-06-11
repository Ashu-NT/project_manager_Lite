from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardWorkspaceViewModel,
)

from .backlog_mapper import backlog_row
from .option_mapper import (
    asset_options,
    location_options,
    site_options,
    system_options,
    window_options,
)
from .overview_mapper import map_overview
from .recurring_mapper import recurring_row
from .root_cause_mapper import root_cause_row


def build_workspace_state(
    desktop_api,
    *,
    site_id: str | None = None,
    asset_id: str | None = None,
    system_id: str | None = None,
    location_id: str | None = None,
    days: int = 90,
) -> MaintenanceDashboardWorkspaceViewModel:
    snapshot = desktop_api.build_snapshot(
        site_id=site_id or None,
        asset_id=asset_id or None,
        system_id=system_id or None,
        location_id=location_id or None,
        days=days,
    )
    return MaintenanceDashboardWorkspaceViewModel(
        overview=map_overview(snapshot.overview),
        site_options=site_options(snapshot),
        selected_site_filter=snapshot.selected_site_id or "all",
        asset_options=asset_options(snapshot),
        selected_asset_filter=snapshot.selected_asset_id or "all",
        system_options=system_options(snapshot),
        selected_system_filter=snapshot.selected_system_id or "all",
        location_options=location_options(snapshot),
        selected_location_filter=snapshot.selected_location_id or "all",
        window_options=window_options(snapshot),
        selected_days_filter=str(snapshot.selected_days),
        backlog_rows=tuple(backlog_row(row) for row in snapshot.backlog_rows),
        root_cause_rows=tuple(root_cause_row(row) for row in snapshot.root_cause_rows),
        recurring_rows=tuple(recurring_row(row) for row in snapshot.recurring_rows),
        empty_state=snapshot.empty_state,
    )
