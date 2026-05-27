from __future__ import annotations

from dataclasses import dataclass, field

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogOverviewViewModel,
    InventoryDetailViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


@dataclass(frozen=True)
class InventoryReservationsWorkspaceViewModel:
    overview: InventoryCatalogOverviewViewModel
    status_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    item_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    storeroom_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_status_filter: str = "all"
    selected_item_filter: str = "all"
    selected_storeroom_filter: str = "all"
    search_text: str = ""
    reservations: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    selected_reservation_id: str = ""
    selected_reservation_detail: InventoryDetailViewModel = field(
        default_factory=InventoryDetailViewModel
    )
    empty_state: str = ""


__all__ = ["InventoryReservationsWorkspaceViewModel"]
