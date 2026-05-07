"""Inventory and procurement repository contracts."""

from src.core.modules.inventory_procurement.contracts.repositories.catalog import (
    InventoryItemCategoryRepository,
    StockItemRepository,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StockBalanceRepository,
    StockReservationRepository,
    StockTransactionRepository,
    StoreroomRepository,
)
from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
    ReceiptHeaderRepository,
    ReceiptLineRepository,
)

__all__ = [
    "InventoryItemCategoryRepository",
    "PurchaseOrderLineRepository",
    "PurchaseOrderRepository",
    "PurchaseRequisitionLineRepository",
    "PurchaseRequisitionRepository",
    "ReceiptHeaderRepository",
    "ReceiptLineRepository",
    "StockBalanceRepository",
    "StockItemRepository",
    "StockReservationRepository",
    "StockTransactionRepository",
    "StoreroomRepository",
]
