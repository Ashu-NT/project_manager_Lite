"""Procurement UI workspaces and dialogs."""

from ui.modules.inventory_procurement.procurement.procurement_dialogs import (
    PurchaseOrderEditDialog,
    PurchaseOrderLineDialog,
    ReceiptPostDialog,
    RequisitionEditDialog,
    RequisitionLineDialog,
)
from ui.modules.inventory_procurement.procurement.purchase_orders_tab import PurchaseOrdersTab
from ui.modules.inventory_procurement.procurement.receiving_tab import ReceivingTab
from ui.modules.inventory_procurement.procurement.requisitions_tab import RequisitionsTab

__all__ = [
    "PurchaseOrderEditDialog",
    "PurchaseOrderLineDialog",
    "ReceiptPostDialog",
    "RequisitionEditDialog",
    "RequisitionLineDialog",
    "PurchaseOrdersTab",
    "ReceivingTab",
    "RequisitionsTab",
]
