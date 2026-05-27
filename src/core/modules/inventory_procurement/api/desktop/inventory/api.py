from __future__ import annotations

from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common.reference_service import (
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
from src.core.modules.inventory_procurement.infrastructure.reporting import (
    InventoryReportingService,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.foundation import (
    InventoryDesktopFoundationMixin,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.options import (
    InventoryDesktopOptionMixin,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.balances import (
    InventoryDesktopBalanceMixin,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.movements import (
    InventoryDesktopMovementMixin,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.storerooms import (
    InventoryDesktopStoreroomMixin,
)


class InventoryProcurementInventoryDesktopApi(
    InventoryDesktopOptionMixin,
    InventoryDesktopFoundationMixin,
    InventoryDesktopStoreroomMixin,
    InventoryDesktopBalanceMixin,
    InventoryDesktopMovementMixin,
):
    def __init__(
        self,
        *,
        inventory_service: InventoryService | None = None,
        stock_service: StockControlService | None = None,
        item_service: ItemMasterService | None = None,
        reference_service: InventoryReferenceService | None = None,
        foundation_service: InventoryFoundationService | None = None,
        reservation_service: ReservationService | None = None,
        procurement_service: ProcurementService | None = None,
        purchasing_service: PurchasingService | None = None,
        reporting_service: InventoryReportingService | None = None,
        module_runtime_service: ModuleRuntimeService | None = None,
    ) -> None:
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._item_service = item_service
        self._reference_service = reference_service
        self._foundation_service = foundation_service
        self._reservation_service = reservation_service
        self._procurement_service = procurement_service
        self._purchasing_service = purchasing_service
        self._reporting_service = reporting_service
        self._module_runtime_service = module_runtime_service

    def _require_inventory_service(self) -> InventoryService:
        if self._inventory_service is None:
            raise RuntimeError("Inventory storeroom desktop API is not connected.")
        return self._inventory_service

    def _require_stock_service(self) -> StockControlService:
        if self._stock_service is None:
            raise RuntimeError("Inventory stock desktop API is not connected.")
        return self._stock_service


def build_inventory_procurement_inventory_desktop_api(
    *,
    inventory_service: InventoryService | None = None,
    stock_service: StockControlService | None = None,
    item_service: ItemMasterService | None = None,
    reference_service: InventoryReferenceService | None = None,
    foundation_service: InventoryFoundationService | None = None,
    reservation_service: ReservationService | None = None,
    procurement_service: ProcurementService | None = None,
    purchasing_service: PurchasingService | None = None,
    reporting_service: InventoryReportingService | None = None,
    module_runtime_service: ModuleRuntimeService | None = None,
) -> InventoryProcurementInventoryDesktopApi:
    return InventoryProcurementInventoryDesktopApi(
        inventory_service=inventory_service,
        stock_service=stock_service,
        item_service=item_service,
        reference_service=reference_service,
        foundation_service=foundation_service,
        reservation_service=reservation_service,
        procurement_service=procurement_service,
        purchasing_service=purchasing_service,
        reporting_service=reporting_service,
        module_runtime_service=module_runtime_service,
    )


__all__ = [
    "InventoryProcurementInventoryDesktopApi",
    "build_inventory_procurement_inventory_desktop_api",
]
