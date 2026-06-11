from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerWorkspaceViewModel,
)

from .material_risk_mapper import material_risk_row
from .option_mapper import (
    asset_options,
    request_queue_options,
    site_options,
    system_options,
    work_order_queue_options,
)
from .overview_mapper import map_overview
from .preventive_mapper import preventive_row
from .recurring_mapper import recurring_row
from .request_mapper import request_row
from .work_order_mapper import work_order_row


def build_workspace_state(
    desktop_api,
    *,
    site_id: str | None = None,
    asset_id: str | None = None,
    system_id: str | None = None,
    request_queue: str = "",
    work_order_queue: str = "",
    search_text: str = "",
) -> MaintenancePlannerWorkspaceViewModel:
    snapshot = desktop_api.build_snapshot(
        site_id=site_id or None,
        asset_id=asset_id or None,
        system_id=system_id or None,
        request_queue=request_queue,
        work_order_queue=work_order_queue,
        search_text=search_text,
    )
    return MaintenancePlannerWorkspaceViewModel(
        overview=map_overview(snapshot.overview),
        site_options=site_options(snapshot),
        selected_site_filter=snapshot.selected_site_id or "all",
        asset_options=asset_options(snapshot),
        selected_asset_filter=snapshot.selected_asset_id or "all",
        system_options=system_options(snapshot),
        selected_system_filter=snapshot.selected_system_id or "all",
        request_queue_options=request_queue_options(snapshot),
        selected_request_queue=snapshot.selected_request_queue,
        work_order_queue_options=work_order_queue_options(snapshot),
        selected_work_order_queue=snapshot.selected_work_order_queue,
        search_text=snapshot.search_text,
        request_rows=tuple(request_row(row) for row in snapshot.request_rows),
        work_order_rows=tuple(work_order_row(row) for row in snapshot.work_order_rows),
        material_rows=tuple(material_risk_row(row) for row in snapshot.material_rows),
        preventive_rows=tuple(preventive_row(row) for row in snapshot.preventive_rows),
        recurring_rows=tuple(recurring_row(row) for row in snapshot.recurring_rows),
        empty_state=snapshot.empty_state,
    )
