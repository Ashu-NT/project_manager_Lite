from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: object


@dataclass(frozen=True)
class StockStatusRow:
    item_code: str
    item_name: str
    storeroom_code: str
    storeroom_name: str
    site_code: str
    uom: str
    on_hand_qty: float
    reserved_qty: float
    available_qty: float
    on_order_qty: float
    average_cost: float
    reorder_required: bool
    last_receipt_at: str = ""
    last_issue_at: str = ""


@dataclass(frozen=True)
class StockStatusReport:
    title: str
    filters: tuple[ReportMetric, ...] = field(default_factory=tuple)
    summary: tuple[ReportMetric, ...] = field(default_factory=tuple)
    rows: tuple[StockStatusRow, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RequisitionOverviewRow:
    requisition_number: str
    status: str
    site_code: str
    storeroom_code: str
    requester_username: str
    needed_by_date: str
    priority: str
    line_count: int
    requested_qty: float
    sourced_qty: float
    purpose: str


@dataclass(frozen=True)
class PurchaseOrderOverviewRow:
    po_number: str
    status: str
    site_code: str
    supplier_code: str
    order_date: str
    expected_delivery_date: str
    line_count: int
    ordered_qty: float
    received_qty: float
    rejected_qty: float
    open_qty: float
    currency_code: str


@dataclass(frozen=True)
class ReceiptOverviewRow:
    receipt_number: str
    purchase_order_number: str
    status: str
    site_code: str
    supplier_code: str
    receipt_date: str
    line_count: int
    accepted_qty: float
    rejected_qty: float
    received_by_username: str


@dataclass(frozen=True)
class ProcurementOverviewReport:
    title: str
    filters: tuple[ReportMetric, ...] = field(default_factory=tuple)
    summary: tuple[ReportMetric, ...] = field(default_factory=tuple)
    requisitions: tuple[RequisitionOverviewRow, ...] = field(default_factory=tuple)
    purchase_orders: tuple[PurchaseOrderOverviewRow, ...] = field(default_factory=tuple)
    receipts: tuple[ReceiptOverviewRow, ...] = field(default_factory=tuple)


__all__ = [
    "ProcurementOverviewReport",
    "PurchaseOrderOverviewRow",
    "ReceiptOverviewRow",
    "ReportMetric",
    "RequisitionOverviewRow",
    "StockStatusReport",
    "StockStatusRow",
]
