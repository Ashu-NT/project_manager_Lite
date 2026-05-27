from __future__ import annotations

from dataclasses import dataclass, field

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogOverviewViewModel,
    InventoryDetailViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


@dataclass(frozen=True)
class InventoryProcurementProcurementWorkspaceViewModel:
    overview: InventoryCatalogOverviewViewModel
    site_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    storeroom_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    supplier_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    requisition_status_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    purchase_order_status_options: tuple[
        InventorySelectorOptionViewModel, ...
    ] = field(default_factory=tuple)
    item_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    requisition_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    requisition_line_options: tuple[InventorySelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    selected_storeroom_filter: str = "all"
    selected_supplier_filter: str = "all"
    selected_requisition_status_filter: str = "all"
    selected_purchase_order_status_filter: str = "all"
    search_text: str = ""
    requisitions: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    selected_requisition_id: str = ""
    selected_requisition_detail: InventoryDetailViewModel = field(
        default_factory=InventoryDetailViewModel
    )
    requisition_lines: tuple[InventoryRecordViewModel, ...] = field(
        default_factory=tuple
    )
    requisitions_empty_state: str = ""
    requisition_lines_empty_state: str = ""
    purchase_orders: tuple[InventoryRecordViewModel, ...] = field(
        default_factory=tuple
    )
    selected_purchase_order_id: str = ""
    selected_purchase_order_detail: InventoryDetailViewModel = field(
        default_factory=InventoryDetailViewModel
    )
    purchase_order_lines: tuple[InventoryRecordViewModel, ...] = field(
        default_factory=tuple
    )
    purchase_orders_empty_state: str = ""
    purchase_order_lines_empty_state: str = ""
    receipts: tuple[InventoryRecordViewModel, ...] = field(default_factory=tuple)
    receipts_empty_state: str = ""
    empty_state: str = ""


__all__ = ["InventoryProcurementProcurementWorkspaceViewModel"]
