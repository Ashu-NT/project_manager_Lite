from __future__ import annotations

from dataclasses import dataclass, field

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogOverviewViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


@dataclass(frozen=True)
class InventoryPricingWorkspaceViewModel:
    overview: InventoryCatalogOverviewViewModel
    context_label: str = ""
    site_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    storeroom_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    supplier_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    limit_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_site_filter: str = "all"
    selected_storeroom_filter: str = "all"
    selected_supplier_filter: str = "all"
    selected_limit_filter: str = "200"
    stock_rows: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    stock_empty_state: str = ""
    supplier_price_rows: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    supplier_price_empty_state: str = ""
    can_export: bool = False
    empty_state: str = ""


__all__ = ["InventoryPricingWorkspaceViewModel"]
