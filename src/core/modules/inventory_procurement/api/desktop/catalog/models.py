from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryCategoryTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryItemStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryDocumentOptionDescriptor:
    value: str
    label: str
    document_type: str
    storage_kind: str
    effective_date_label: str
    is_active: bool


@dataclass(frozen=True)
class InventoryCategoryDesktopDto:
    id: str
    category_code: str
    name: str
    description: str
    category_type: str
    category_type_label: str
    is_equipment: bool
    supports_project_usage: bool
    supports_maintenance_usage: bool
    is_active: bool
    active_label: str
    version: int


@dataclass(frozen=True)
class InventoryItemDesktopDto:
    id: str
    item_code: str
    name: str
    description: str
    item_type: str
    status: str
    status_label: str
    stock_uom: str
    order_uom: str
    issue_uom: str
    order_uom_ratio: float
    order_uom_ratio_label: str
    issue_uom_ratio: float
    issue_uom_ratio_label: str
    category_code: str
    category_label: str
    commodity_code: str
    is_stocked: bool
    is_purchase_allowed: bool
    is_active: bool
    active_label: str
    default_reorder_policy: str
    min_qty: float
    min_qty_label: str
    max_qty: float
    max_qty_label: str
    reorder_point: float
    reorder_point_label: str
    reorder_qty: float
    reorder_qty_label: str
    lead_time_days: int | None
    shelf_life_days: int | None
    is_lot_tracked: bool
    is_serial_tracked: bool
    preferred_party_id: str | None
    preferred_party_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryCategoryCreateCommand:
    category_code: str
    name: str
    description: str = ""
    category_type: str = "MATERIAL"
    is_equipment: bool = False
    supports_project_usage: bool = False
    supports_maintenance_usage: bool = False
    is_active: bool = True


@dataclass(frozen=True)
class InventoryCategoryUpdateCommand:
    category_id: str
    category_code: str
    name: str
    description: str = ""
    category_type: str = "MATERIAL"
    is_equipment: bool = False
    supports_project_usage: bool = False
    supports_maintenance_usage: bool = False
    is_active: bool = True
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryItemCreateCommand:
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str | None = None
    issue_uom: str | None = None
    order_uom_ratio: float | None = None
    issue_uom_ratio: float | None = None
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryItemUpdateCommand:
    item_id: str
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str | None = None
    issue_uom: str | None = None
    order_uom_ratio: float | None = None
    issue_uom_ratio: float | None = None
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    notes: str = ""
    expected_version: int | None = None


__all__ = [
    "InventoryCategoryCreateCommand",
    "InventoryCategoryDesktopDto",
    "InventoryCategoryTypeDescriptor",
    "InventoryCategoryUpdateCommand",
    "InventoryDocumentOptionDescriptor",
    "InventoryItemCreateCommand",
    "InventoryItemDesktopDto",
    "InventoryItemStatusDescriptor",
    "InventoryItemUpdateCommand",
]
