from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.core.modules.inventory_procurement import (
    InventoryFoundationService,
    InventoryReferenceService,
    InventoryReportingService,
    InventoryService,
    ItemCategoryService,
    ItemMasterService,
    ProcurementService,
    PurchasingService,
    ReservationService,
    StockControlService,
)


@dataclass(frozen=True)
class InventoryProcurementDesktopRuntimeServices:
    reference_service: InventoryReferenceService | None
    category_service: ItemCategoryService | None
    item_service: ItemMasterService | None
    foundation_service: InventoryFoundationService | None
    inventory_service: InventoryService | None
    stock_service: StockControlService | None
    reservation_service: ReservationService | None
    procurement_service: ProcurementService | None
    purchasing_service: PurchasingService | None
    reporting_service: InventoryReportingService | None


def resolve_inventory_procurement_desktop_runtime_services(
    services: Mapping[str, object],
) -> InventoryProcurementDesktopRuntimeServices:
    reference_service = services.get("inventory_reference_service")
    category_service = services.get("inventory_item_category_service")
    item_service = services.get("inventory_item_service")
    foundation_service = services.get("inventory_foundation_service")
    inventory_service = services.get("inventory_service")
    stock_service = services.get("inventory_stock_service")
    reservation_service = services.get("inventory_reservation_service")
    procurement_service = services.get("inventory_procurement_service")
    purchasing_service = services.get("inventory_purchasing_service")
    reporting_service = services.get("inventory_reporting_service")
    return InventoryProcurementDesktopRuntimeServices(
        reference_service=(
            reference_service
            if isinstance(reference_service, InventoryReferenceService)
            else None
        ),
        category_service=(
            category_service
            if isinstance(category_service, ItemCategoryService)
            else None
        ),
        item_service=(
            item_service if isinstance(item_service, ItemMasterService) else None
        ),
        foundation_service=(
            foundation_service
            if isinstance(foundation_service, InventoryFoundationService)
            else None
        ),
        inventory_service=(
            inventory_service if isinstance(inventory_service, InventoryService) else None
        ),
        stock_service=(
            stock_service if isinstance(stock_service, StockControlService) else None
        ),
        reservation_service=(
            reservation_service
            if isinstance(reservation_service, ReservationService)
            else None
        ),
        procurement_service=(
            procurement_service
            if isinstance(procurement_service, ProcurementService)
            else None
        ),
        purchasing_service=(
            purchasing_service
            if isinstance(purchasing_service, PurchasingService)
            else None
        ),
        reporting_service=(
            reporting_service
            if isinstance(reporting_service, InventoryReportingService)
            else None
        ),
    )


__all__ = [
    "InventoryProcurementDesktopRuntimeServices",
    "resolve_inventory_procurement_desktop_runtime_services",
]
