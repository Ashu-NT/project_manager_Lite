from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementCatalogDesktopApi,
    InventoryProcurementDashboardDesktopApi,
    InventoryProcurementInventoryDesktopApi,
    InventoryProcurementPricingDesktopApi,
    InventoryProcurementProcurementDesktopApi,
    InventoryProcurementReservationsDesktopApi,
    InventoryProcurementWorkspaceDesktopApi,
)


@dataclass(frozen=True)
class InventoryProcurementDesktopRuntimeApis:
    inventory_procurement_workspaces: InventoryProcurementWorkspaceDesktopApi
    inventory_procurement_catalog: InventoryProcurementCatalogDesktopApi
    inventory_procurement_inventory: InventoryProcurementInventoryDesktopApi
    inventory_procurement_reservations: InventoryProcurementReservationsDesktopApi
    inventory_procurement_procurement: InventoryProcurementProcurementDesktopApi
    inventory_procurement_dashboard: InventoryProcurementDashboardDesktopApi
    inventory_procurement_pricing: InventoryProcurementPricingDesktopApi


@dataclass(frozen=True)
class InventoryProcurementDesktopRuntimePlatformDependencies:
    module_runtime_service: object | None
    user_session: object | None


__all__ = [
    "InventoryProcurementDesktopRuntimeApis",
    "InventoryProcurementDesktopRuntimePlatformDependencies",
]
