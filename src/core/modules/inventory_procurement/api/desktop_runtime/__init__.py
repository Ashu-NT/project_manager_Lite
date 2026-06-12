"""Inventory and procurement desktop runtime composition."""

from src.core.modules.inventory_procurement.api.desktop_runtime.desktop_api_builder import (
    build_inventory_procurement_desktop_runtime_apis,
)
from src.core.modules.inventory_procurement.api.desktop_runtime.registry import (
    InventoryProcurementDesktopRuntimeApis,
    InventoryProcurementDesktopRuntimePlatformDependencies,
)

__all__ = [
    "InventoryProcurementDesktopRuntimeApis",
    "InventoryProcurementDesktopRuntimePlatformDependencies",
    "build_inventory_procurement_desktop_runtime_apis",
]
