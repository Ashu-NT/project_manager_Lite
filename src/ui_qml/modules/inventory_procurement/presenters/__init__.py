"""Inventory procurement QML presenters."""

from src.ui_qml.modules.inventory_procurement.presenters.catalog import (
    InventoryCatalogWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.dashboard_workspace_presenter import (
    InventoryDashboardWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.inventory import (
    InventoryInventoryWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.pricing_workspace_presenter import (
    InventoryPricingWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.procurement import (
    InventoryProcurementProcurementWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.reservations_workspace_presenter import (
    InventoryReservationsWorkspacePresenter,
)
from src.ui_qml.modules.inventory_procurement.presenters.workspace_presenter import (
    InventoryProcurementWorkspacePresenter,
    build_inventory_procurement_workspace_presenters,
)

__all__ = [
    "InventoryCatalogWorkspacePresenter",
    "InventoryDashboardWorkspacePresenter",
    "InventoryInventoryWorkspacePresenter",
    "InventoryPricingWorkspacePresenter",
    "InventoryProcurementProcurementWorkspacePresenter",
    "InventoryProcurementWorkspacePresenter",
    "InventoryReservationsWorkspacePresenter",
    "build_inventory_procurement_workspace_presenters",
]
