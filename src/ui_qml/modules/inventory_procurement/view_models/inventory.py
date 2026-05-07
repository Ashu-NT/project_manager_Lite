from __future__ import annotations

from dataclasses import dataclass, field

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogOverviewViewModel,
    InventoryDetailViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


@dataclass(frozen=True)
class InventoryInventoryWorkspaceViewModel:
    overview: InventoryCatalogOverviewViewModel
    site_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    active_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    storeroom_status_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    transaction_type_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    storeroom_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    item_options: tuple[InventorySelectorOptionViewModel, ...] = field(default_factory=tuple)
    manager_party_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    selected_active_filter: str = "all"
    selected_storeroom_filter: str = "all"
    selected_item_filter: str = "all"
    selected_transaction_type_filter: str = "all"
    search_text: str = ""
    storerooms: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    selected_storeroom_id: str = ""
    selected_storeroom_detail: InventoryDetailViewModel = field(
        default_factory=InventoryDetailViewModel
    )
    balances: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    selected_balance_id: str = ""
    selected_balance_detail: InventoryDetailViewModel = field(
        default_factory=InventoryDetailViewModel
    )
    transactions: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = ["InventoryInventoryWorkspaceViewModel"]
