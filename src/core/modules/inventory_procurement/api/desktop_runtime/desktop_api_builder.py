from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.inventory_procurement.api.desktop import (
    build_inventory_procurement_catalog_desktop_api,
    build_inventory_procurement_dashboard_desktop_api,
    build_inventory_procurement_inventory_desktop_api,
    build_inventory_procurement_pricing_desktop_api,
    build_inventory_procurement_procurement_desktop_api,
    build_inventory_procurement_reservations_desktop_api,
    build_inventory_procurement_workspace_desktop_api,
)
from src.core.modules.inventory_procurement.api.desktop_runtime.registry import (
    InventoryProcurementDesktopRuntimeApis,
    InventoryProcurementDesktopRuntimePlatformDependencies,
)
from src.core.modules.inventory_procurement.api.desktop_runtime.service_resolver import (
    resolve_inventory_procurement_desktop_runtime_services,
)


def build_inventory_procurement_desktop_runtime_apis(
    services: Mapping[str, object],
    platform_dependencies: InventoryProcurementDesktopRuntimePlatformDependencies,
) -> InventoryProcurementDesktopRuntimeApis:
    resolved = resolve_inventory_procurement_desktop_runtime_services(services)
    return InventoryProcurementDesktopRuntimeApis(
        inventory_procurement_workspaces=build_inventory_procurement_workspace_desktop_api(),
        inventory_procurement_catalog=build_inventory_procurement_catalog_desktop_api(
            category_service=resolved.category_service,
            item_service=resolved.item_service,
            reference_service=resolved.reference_service,
        ),
        inventory_procurement_inventory=build_inventory_procurement_inventory_desktop_api(
            inventory_service=resolved.inventory_service,
            stock_service=resolved.stock_service,
            item_service=resolved.item_service,
            reference_service=resolved.reference_service,
            foundation_service=resolved.foundation_service,
            reservation_service=resolved.reservation_service,
            procurement_service=resolved.procurement_service,
            purchasing_service=resolved.purchasing_service,
            reporting_service=resolved.reporting_service,
            module_runtime_service=platform_dependencies.module_runtime_service,
        ),
        inventory_procurement_reservations=build_inventory_procurement_reservations_desktop_api(
            reservation_service=resolved.reservation_service,
            item_service=resolved.item_service,
            inventory_service=resolved.inventory_service,
        ),
        inventory_procurement_procurement=build_inventory_procurement_procurement_desktop_api(
            procurement_service=resolved.procurement_service,
            purchasing_service=resolved.purchasing_service,
            reference_service=resolved.reference_service,
            inventory_service=resolved.inventory_service,
            item_service=resolved.item_service,
        ),
        inventory_procurement_dashboard=build_inventory_procurement_dashboard_desktop_api(
            item_service=resolved.item_service,
            inventory_service=resolved.inventory_service,
            stock_service=resolved.stock_service,
            reservation_service=resolved.reservation_service,
            procurement_service=resolved.procurement_service,
            purchasing_service=resolved.purchasing_service,
            reference_service=resolved.reference_service,
        ),
        inventory_procurement_pricing=build_inventory_procurement_pricing_desktop_api(
            reporting_service=resolved.reporting_service,
            reference_service=resolved.reference_service,
            inventory_service=resolved.inventory_service,
            purchasing_service=resolved.purchasing_service,
            item_service=resolved.item_service,
            user_session=platform_dependencies.user_session,
        ),
    )


__all__ = ["build_inventory_procurement_desktop_runtime_apis"]
