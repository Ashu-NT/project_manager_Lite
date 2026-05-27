from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_amount,
    format_date,
    format_datetime,
    format_enum_label,
    format_quantity,
)


@dataclass(frozen=True)
class InventoryPurchaseOrderDesktopDto:
    id: str
    po_number: str
    site_id: str
    site_label: str
    supplier_party_id: str
    supplier_label: str
    status: str
    status_label: str
    order_date: date | None
    order_date_label: str
    expected_delivery_date: date | None
    expected_delivery_date_label: str
    currency_code: str
    approval_request_id: str | None
    source_requisition_id: str | None
    source_requisition_label: str
    supplier_reference: str
    submitted_at_label: str
    approved_at_label: str
    sent_at_label: str
    closed_at_label: str
    cancelled_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryPurchaseOrderLineDesktopDto:
    id: str
    purchase_order_id: str
    line_number: int
    stock_item_id: str
    stock_item_label: str
    destination_storeroom_id: str
    destination_storeroom_label: str
    description: str
    quantity_ordered: float
    quantity_ordered_label: str
    quantity_received: float
    quantity_received_label: str
    quantity_rejected: float
    quantity_rejected_label: str
    uom: str
    unit_price: float
    unit_price_label: str
    expected_delivery_date: date | None
    expected_delivery_date_label: str
    source_requisition_line_id: str | None
    status: str
    status_label: str
    notes: str


@dataclass(frozen=True)
class InventoryPurchaseOrderCreateCommand:
    site_id: str
    supplier_party_id: str
    currency_code: str | None = None
    source_requisition_id: str | None = None
    order_date: date | None = None
    expected_delivery_date: date | None = None
    supplier_reference: str = ""
    notes: str = ""
    po_number: str | None = None


@dataclass(frozen=True)
class InventoryPurchaseOrderUpdateCommand:
    purchase_order_id: str
    site_id: str
    supplier_party_id: str
    currency_code: str | None = None
    source_requisition_id: str | None = None
    expected_delivery_date: date | None = None
    supplier_reference: str = ""
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryPurchaseOrderLineCreateCommand:
    purchase_order_id: str
    stock_item_id: str
    destination_storeroom_id: str
    quantity_ordered: float
    uom: str | None = None
    unit_price: float = 0.0
    expected_delivery_date: date | None = None
    description: str = ""
    source_requisition_line_id: str | None = None
    notes: str = ""


def serialize_purchase_order(
    row,
    *,
    site_lookup: dict[str, str],
    supplier_lookup: dict[str, str],
    requisition_lookup: dict[str, str],
) -> InventoryPurchaseOrderDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    source_requisition_id = clean_text(getattr(row, "source_requisition_id", "")) or None
    return InventoryPurchaseOrderDesktopDto(
        id=row.id,
        po_number=clean_text(getattr(row, "po_number", "")),
        site_id=clean_text(getattr(row, "site_id", "")),
        site_label=site_lookup.get(clean_text(getattr(row, "site_id", "")), "-"),
        supplier_party_id=clean_text(getattr(row, "supplier_party_id", "")),
        supplier_label=supplier_lookup.get(clean_text(getattr(row, "supplier_party_id", "")), "-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        order_date=getattr(row, "order_date", None),
        order_date_label=format_date(getattr(row, "order_date", None)),
        expected_delivery_date=getattr(row, "expected_delivery_date", None),
        expected_delivery_date_label=format_date(getattr(row, "expected_delivery_date", None)),
        currency_code=clean_text(getattr(row, "currency_code", "")),
        approval_request_id=clean_text(getattr(row, "approval_request_id", "")) or None,
        source_requisition_id=source_requisition_id,
        source_requisition_label=requisition_lookup.get(source_requisition_id or "", "-"),
        supplier_reference=clean_text(getattr(row, "supplier_reference", "")),
        submitted_at_label=format_datetime(getattr(row, "submitted_at", None)),
        approved_at_label=format_datetime(getattr(row, "approved_at", None)),
        sent_at_label=format_datetime(getattr(row, "sent_at", None)),
        closed_at_label=format_datetime(getattr(row, "closed_at", None)),
        cancelled_at_label=format_datetime(getattr(row, "cancelled_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_purchase_order_line(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryPurchaseOrderLineDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryPurchaseOrderLineDesktopDto(
        id=row.id,
        purchase_order_id=clean_text(getattr(row, "purchase_order_id", "")),
        line_number=int(getattr(row, "line_number", 0) or 0),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        destination_storeroom_id=clean_text(getattr(row, "destination_storeroom_id", "")),
        destination_storeroom_label=storeroom_lookup.get(
            clean_text(getattr(row, "destination_storeroom_id", "")),
            "-",
        ),
        description=clean_text(getattr(row, "description", "")),
        quantity_ordered=float(getattr(row, "quantity_ordered", 0.0) or 0.0),
        quantity_ordered_label=format_quantity(getattr(row, "quantity_ordered", 0.0)),
        quantity_received=float(getattr(row, "quantity_received", 0.0) or 0.0),
        quantity_received_label=format_quantity(getattr(row, "quantity_received", 0.0)),
        quantity_rejected=float(getattr(row, "quantity_rejected", 0.0) or 0.0),
        quantity_rejected_label=format_quantity(getattr(row, "quantity_rejected", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        unit_price=float(getattr(row, "unit_price", 0.0) or 0.0),
        unit_price_label=format_amount(getattr(row, "unit_price", 0.0)),
        expected_delivery_date=getattr(row, "expected_delivery_date", None),
        expected_delivery_date_label=format_date(getattr(row, "expected_delivery_date", None)),
        source_requisition_line_id=clean_text(getattr(row, "source_requisition_line_id", "")) or None,
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        notes=clean_text(getattr(row, "notes", "")),
    )


__all__ = [
    "InventoryPurchaseOrderCreateCommand",
    "InventoryPurchaseOrderDesktopDto",
    "InventoryPurchaseOrderLineCreateCommand",
    "InventoryPurchaseOrderLineDesktopDto",
    "InventoryPurchaseOrderUpdateCommand",
    "serialize_purchase_order",
    "serialize_purchase_order_line",
]
