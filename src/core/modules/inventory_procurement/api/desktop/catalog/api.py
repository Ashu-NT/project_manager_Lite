from __future__ import annotations

from src.core.modules.inventory_procurement.application.catalog import (
    ItemCategoryService,
    ItemMasterService,
)
from src.core.modules.inventory_procurement.application.common.reference_service import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.categories import (
    InventoryCatalogDesktopCategoryMixin,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.items import (
    InventoryCatalogDesktopItemMixin,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.options import (
    InventoryCatalogDesktopOptionMixin,
)


class InventoryProcurementCatalogDesktopApi(
    InventoryCatalogDesktopOptionMixin,
    InventoryCatalogDesktopCategoryMixin,
    InventoryCatalogDesktopItemMixin,
):
    def __init__(
        self,
        *,
        category_service: ItemCategoryService | None = None,
        item_service: ItemMasterService | None = None,
        reference_service: InventoryReferenceService | None = None,
    ) -> None:
        self._category_service = category_service
        self._item_service = item_service
        self._reference_service = reference_service

    def _require_category_service(self) -> ItemCategoryService:
        if self._category_service is None:
            raise RuntimeError("Inventory catalog category desktop API is not connected.")
        return self._category_service

    def _require_item_service(self) -> ItemMasterService:
        if self._item_service is None:
            raise RuntimeError("Inventory catalog item desktop API is not connected.")
        return self._item_service


def build_inventory_procurement_catalog_desktop_api(
    *,
    category_service: ItemCategoryService | None = None,
    item_service: ItemMasterService | None = None,
    reference_service: InventoryReferenceService | None = None,
) -> InventoryProcurementCatalogDesktopApi:
    return InventoryProcurementCatalogDesktopApi(
        category_service=category_service,
        item_service=item_service,
        reference_service=reference_service,
    )


__all__ = [
    "InventoryProcurementCatalogDesktopApi",
    "build_inventory_procurement_catalog_desktop_api",
]
