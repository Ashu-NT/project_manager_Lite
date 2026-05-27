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
class InventoryLocationTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryCycleCountStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryFoundationMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class InventoryModuleLinkDescriptor:
    code: str
    label: str
    kind: str
    is_enabled: bool
    status_label: str
    reason: str
    route_id: str


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
class InventoryStorageLocationDesktopDto:
    id: str
    storeroom_id: str
    storeroom_label: str
    location_code: str
    name: str
    parent_location_id: str | None
    parent_location_label: str
    location_type: str
    location_type_label: str
    is_active: bool
    active_label: str
    is_quarantine: bool
    quarantine_label: str
    allows_issue: bool
    allows_putaway: bool
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryReorderPolicyDesktopDto:
    id: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    location_id: str | None
    location_label: str
    policy_name: str
    is_active: bool
    active_label: str
    min_qty: float
    min_qty_label: str
    max_qty: float
    max_qty_label: str
    reorder_point: float
    reorder_point_label: str
    reorder_qty: float
    reorder_qty_label: str
    economic_order_qty: float
    economic_order_qty_label: str
    lead_time_days: int | None
    lead_time_days_label: str
    review_period_days: int | None
    review_period_days_label: str
    preferred_supplier_party_id: str | None
    preferred_supplier_label: str
    version: int


@dataclass(frozen=True)
class InventoryCycleCountDesktopDto:
    id: str
    cycle_count_number: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    location_id: str | None
    location_label: str
    scheduled_count_date_label: str
    status: str
    status_label: str
    expected_qty: float
    expected_qty_label: str
    counted_qty: float | None
    counted_qty_label: str
    variance_qty: float
    variance_qty_label: str
    counted_by_username: str
    completed_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryFoundationSignalDesktopDto:
    id: str
    title: str
    subtitle: str
    status_label: str
    supporting_text: str
    meta_text: str
    tone: str = "default"


@dataclass(frozen=True)
class InventoryFoundationSnapshotDesktopDto:
    title: str
    subtitle: str
    metrics: tuple[InventoryFoundationMetricDescriptor, ...]
    module_links: tuple[InventoryModuleLinkDescriptor, ...]
    locations: tuple[InventoryStorageLocationDesktopDto, ...]
    reorder_policies: tuple[InventoryReorderPolicyDesktopDto, ...]
    cycle_counts: tuple[InventoryCycleCountDesktopDto, ...]
    valuation_signals: tuple[InventoryFoundationSignalDesktopDto, ...]
    tracking_signals: tuple[InventoryFoundationSignalDesktopDto, ...]
    activity_signals: tuple[InventoryFoundationSignalDesktopDto, ...]


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


@dataclass(frozen=True)
class InventoryLocationCreateCommand:
    storeroom_id: str
    location_code: str
    name: str
    parent_location_id: str | None = None
    location_type: str = "BIN"
    is_active: bool = True
    is_quarantine: bool = False
    allows_issue: bool = True
    allows_putaway: bool = True
    notes: str = ""


@dataclass(frozen=True)
class InventoryLocationUpdateCommand:
    location_id: str
    location_code: str
    name: str
    parent_location_id: str | None = None
    location_type: str = "BIN"
    is_active: bool = True
    is_quarantine: bool = False
    allows_issue: bool = True
    allows_putaway: bool = True
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryReorderPolicyUpsertCommand:
    stock_item_id: str
    storeroom_id: str
    location_id: str | None = None
    policy_name: str = ""
    is_active: bool = True
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    economic_order_qty: float = 0.0
    lead_time_days: int | None = None
    review_period_days: int | None = None
    preferred_supplier_party_id: str | None = None
    policy_id: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryCycleCountCreateCommand:
    stock_item_id: str
    storeroom_id: str
    location_id: str | None = None
    scheduled_count_date: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryCycleCountCompleteCommand:
    cycle_count_id: str
    counted_qty: float
    notes: str = ""
    expected_version: int | None = None


__all__ = [
    "InventoryAdjustmentCommand",
    "InventoryCycleCountCompleteCommand",
    "InventoryCycleCountCreateCommand",
    "InventoryCycleCountDesktopDto",
    "InventoryCycleCountStatusDescriptor",
    "InventoryFoundationMetricDescriptor",
    "InventoryFoundationSignalDesktopDto",
    "InventoryFoundationSnapshotDesktopDto",
    "InventoryIssueCommand",
    "InventoryLocationCreateCommand",
    "InventoryLocationTypeDescriptor",
    "InventoryLocationUpdateCommand",
    "InventoryModuleLinkDescriptor",
    "InventoryOpeningBalanceCommand",
    "InventoryReorderPolicyDesktopDto",
    "InventoryReorderPolicyUpsertCommand",
    "InventoryReturnCommand",
    "InventoryStorageLocationDesktopDto",
    "InventoryStockBalanceDesktopDto",
    "InventoryStockTransactionDesktopDto",
    "InventoryStoreroomCreateCommand",
    "InventoryStoreroomDesktopDto",
    "InventoryStoreroomStatusDescriptor",
    "InventoryStoreroomUpdateCommand",
    "InventoryTransactionTypeDescriptor",
    "InventoryTransferCommand",
]
