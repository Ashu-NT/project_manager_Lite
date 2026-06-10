from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardWorkspaceViewModel,
)

from .overview_mapper import build_overview
from .section_mapper import to_section_view_model


def build_workspace_state(desktop_api) -> InventoryDashboardWorkspaceViewModel:
    snapshot = desktop_api.build_snapshot()
    return InventoryDashboardWorkspaceViewModel(
        overview=build_overview(snapshot),
        context_label=snapshot.context_label,
        sections=tuple(to_section_view_model(section) for section in snapshot.sections),
        empty_state=snapshot.empty_state,
    )
