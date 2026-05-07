from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class InventoryStoreroomStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryTransactionTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryStoreroomDesktopDto:
    id: str
    storeroom_code: str
    name: str
    description: str
    site_id: str
    site_label: str
    status: str
    status_label: str
    storeroom_type: str
    is_active: bool
    active_label: str
    is_internal_supplier: bool
    allows_issue: bool
    allows_transfer: bool
    allows_receiving: bool
    requires_reservation_for_issue: bool
    requires_supplier_reference_for_receipt: bool
    default_currency_code: str
    manager_party_id: str | None
    manager_party_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryStockBalanceDesktopDto:
    id: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    uom: str
    on_hand_qty: float
    on_hand_qty_label: str
    reserved_qty: float
    reserved_qty_label: str
    available_qty: float
    available_qty_label: str
    on_order_qty: float
    on_order_qty_label: str
    committed_qty: float
    committed_qty_label: str
    average_cost: float
    average_cost_label: str
    last_receipt_at_label: str
    last_issue_at_label: str
    reorder_required: bool
    version: int


@dataclass(frozen=True)
class InventoryStockTransactionDesktopDto:
    id: str
    transaction_number: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    transaction_type: str
    transaction_type_label: str
    quantity: float
    quantity_label: str
    uom: str
    unit_cost: float
    unit_cost_label: str
    transaction_at_label: str
    reference_type: str
    reference_id: str
    performed_by_username: str
    resulting_on_hand_qty_label: str
    resulting_available_qty_label: str
    notes: str


@dataclass(frozen=True)
class InventoryStoreroomCreateCommand:
    storeroom_code: str
    name: str
    site_id: str
    description: str = ""
    status: str = "DRAFT"
    storeroom_type: str = ""
    is_internal_supplier: bool = False
    allows_issue: bool = True
    allows_transfer: bool = True
    allows_receiving: bool = True
    requires_reservation_for_issue: bool = False
    requires_supplier_reference_for_receipt: bool = False
    default_currency_code: str | None = None
    manager_party_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryStoreroomUpdateCommand:
    storeroom_id: str
    storeroom_code: str
    name: str
    site_id: str
    description: str = ""
    status: str = "DRAFT"
    storeroom_type: str = ""
    is_internal_supplier: bool = False
    allows_issue: bool = True
    allows_transfer: bool = True
    allows_receiving: bool = True
    requires_reservation_for_issue: bool = False
    requires_supplier_reference_for_receipt: bool = False
    default_currency_code: str | None = None
    manager_party_id: str | None = None
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryOpeningBalanceCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    uom: str | None = None
    unit_cost: float = 0.0
    transaction_at: datetime | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryAdjustmentCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    direction: str
    uom: str | None = None
    unit_cost: float = 0.0
    transaction_at: datetime | None = None
    reference_type: str = "adjustment"
    reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryIssueCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    uom: str | None = None
    unit_cost: float | None = None
    transaction_at: datetime | None = None
    release_reserved_qty: float = 0.0
    reference_type: str = "issue"
    reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryReturnCommand:
    stock_item_id: str
    storeroom_id: str
    quantity: float
    uom: str | None = None
    unit_cost: float | None = None
    transaction_at: datetime | None = None
    reference_type: str = "return"
    reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryTransferCommand:
    stock_item_id: str
    source_storeroom_id: str
    destination_storeroom_id: str
    quantity: float
    uom: str | None = None
    transaction_at: datetime | None = None
    notes: str = ""


__all__ = [
    "InventoryAdjustmentCommand",
    "InventoryIssueCommand",
    "InventoryOpeningBalanceCommand",
    "InventoryReturnCommand",
    "InventoryStockBalanceDesktopDto",
    "InventoryStockTransactionDesktopDto",
    "InventoryStoreroomCreateCommand",
    "InventoryStoreroomDesktopDto",
    "InventoryStoreroomStatusDescriptor",
    "InventoryStoreroomUpdateCommand",
    "InventoryTransactionTypeDescriptor",
    "InventoryTransferCommand",
]
