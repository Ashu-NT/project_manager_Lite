from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementDashboardDesktopApi,
    build_inventory_procurement_dashboard_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardWorkspaceViewModel,
)

from .workspace_builder import build_workspace_state


class InventoryDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = (
            desktop_api or build_inventory_procurement_dashboard_desktop_api()
        )

    def build_workspace_state(self) -> InventoryDashboardWorkspaceViewModel:
        return build_workspace_state(self._desktop_api)
