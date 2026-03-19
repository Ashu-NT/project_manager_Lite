"""User-interface package for the Inventory & Procurement module."""

from ui.modules.inventory_procurement.items_tab import InventoryItemsTab
from ui.modules.inventory_procurement.movements_tab import MovementsTab
from ui.modules.inventory_procurement.purchase_orders_tab import PurchaseOrdersTab
from ui.modules.inventory_procurement.receiving_tab import ReceivingTab
from ui.modules.inventory_procurement.reservations_tab import ReservationsTab
from ui.modules.inventory_procurement.requisitions_tab import RequisitionsTab
from ui.modules.inventory_procurement.stock_tab import StockTab
from ui.modules.inventory_procurement.storerooms_tab import StoreroomsTab

__all__ = [
    "InventoryItemsTab",
    "MovementsTab",
    "PurchaseOrdersTab",
    "ReceivingTab",
    "ReservationsTab",
    "RequisitionsTab",
    "StockTab",
    "StoreroomsTab",
]
