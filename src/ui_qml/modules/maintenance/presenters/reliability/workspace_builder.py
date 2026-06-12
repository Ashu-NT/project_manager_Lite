from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityWorkspaceViewModel,
)

from .option_mapper import (
    asset_options,
    days_options,
    failure_symptom_options,
    limit_options,
    location_options,
    site_options,
    system_options,
    threshold_options,
)
from .overview_mapper import map_overview
from .recurring_mapper import recurring_row
from .root_cause_mapper import root_cause_row
from .suggestion_mapper import suggestion_row


def build_workspace_state(
    desktop_api,
    *,
    site_id: str | None = None,
    asset_id: str | None = None,
    system_id: str | None = None,
    location_id: str | None = None,
    failure_code: str | None = None,
    days: int = 90,
    limit: int = 20,
    threshold: int = 2,
) -> MaintenanceReliabilityWorkspaceViewModel:
    snapshot = desktop_api.build_snapshot(
        site_id=site_id or None,
        asset_id=asset_id or None,
        system_id=system_id or None,
        location_id=location_id or None,
        failure_code=failure_code or None,
        days=days,
        limit=limit,
        threshold=threshold,
    )
    return MaintenanceReliabilityWorkspaceViewModel(
        overview=map_overview(snapshot.overview),
        site_options=site_options(snapshot),
        selected_site_filter=snapshot.selected_site_id or "all",
        asset_options=asset_options(snapshot),
        selected_asset_filter=snapshot.selected_asset_id or "all",
        system_options=system_options(snapshot),
        selected_system_filter=snapshot.selected_system_id or "all",
        location_options=location_options(snapshot),
        selected_location_filter=snapshot.selected_location_id or "all",
        failure_symptom_options=failure_symptom_options(snapshot),
        selected_failure_code_filter=snapshot.selected_failure_code or "all",
        days_options=days_options(snapshot),
        selected_days_filter=str(snapshot.selected_days),
        limit_options=limit_options(snapshot),
        selected_limit_filter=str(snapshot.selected_limit),
        threshold_options=threshold_options(snapshot),
        selected_threshold_filter=str(snapshot.selected_threshold),
        suggestion_rows=tuple(suggestion_row(row) for row in snapshot.suggestion_rows),
        root_cause_rows=tuple(root_cause_row(row) for row in snapshot.root_cause_rows),
        recurring_rows=tuple(recurring_row(row) for row in snapshot.recurring_rows),
        empty_state=snapshot.empty_state,
    )
