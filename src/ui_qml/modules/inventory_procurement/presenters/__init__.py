"""Inventory and procurement QML presenters."""
"""Inventory procurement QML presenters."""

from src.ui_qml.modules.inventory_procurement.presenters.catalog_workspace_presenter import (
    InventoryCatalogWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.dashboard_workspace_presenter import (
    InventoryDashboardWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.workspace_presenter import (
    InventoryProcurementWorkspacePresenter,
    build_inventory_procurement_workspace_presenters,
)

__all__ = [
    "InventoryCatalogWorkspacePresenter",
    "InventoryDashboardWorkspacePresenter",
    "InventoryProcurementWorkspacePresenter",
    "build_inventory_procurement_workspace_presenters",
]
