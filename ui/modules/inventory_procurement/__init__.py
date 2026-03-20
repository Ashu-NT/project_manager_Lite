"""User-interface package for the Inventory & Procurement module."""

from ui.modules.inventory_procurement.dashboard_tab import InventoryDashboardTab
from ui.modules.inventory_procurement.inventory import StoreroomsTab
from ui.modules.inventory_procurement.item_master import InventoryItemsTab
from ui.modules.inventory_procurement.procurement import (
    PurchaseOrdersTab,
    ReceivingTab,
    RequisitionsTab,
)
from ui.modules.inventory_procurement.reservation import ReservationsTab
from ui.modules.inventory_procurement.stock_control import MovementsTab, StockTab

__all__ = [
    "InventoryDashboardTab",
    "InventoryItemsTab",
    "MovementsTab",
    "PurchaseOrdersTab",
    "ReceivingTab",
    "ReservationsTab",
    "RequisitionsTab",
    "StockTab",
    "StoreroomsTab",
]
