"""Inventory and procurement module."""

from src.core.modules.inventory_procurement.application.catalog import (
    ItemCategoryService,
    ItemMasterService,
)
from src.core.modules.inventory_procurement.application.common import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryFoundationService,
    InventoryService,
    ReservationService,
    StockControlService,
)
from src.core.modules.inventory_procurement.application.procurement import (
    ProcurementService,
    PurchasingService,
)
from src.core.modules.inventory_procurement.infrastructure.importers import (
    InventoryDataExchangeService,
)
from src.core.modules.inventory_procurement.infrastructure.integrations import (
    MaintenanceMaterialService,
)
from src.core.modules.inventory_procurement.infrastructure.reporting import (
    InventoryReportingService,
)

__all__ = [
    "InventoryDataExchangeService",
    "InventoryFoundationService",
    "InventoryReferenceService",
    "InventoryReportingService",
    "ItemCategoryService",
    "ItemMasterService",
    "InventoryService",
    "MaintenanceMaterialService",
    "ProcurementService",
    "PurchasingService",
    "ReservationService",
    "StockControlService",
]
