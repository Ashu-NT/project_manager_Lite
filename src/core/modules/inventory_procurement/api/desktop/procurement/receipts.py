from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_amount,
    format_date,
    format_datetime,
    format_enum_label,
    format_quantity,
)


@dataclass(frozen=True)
class InventoryReceiptDesktopDto:
    id: str
    receipt_number: str
    purchase_order_id: str
    purchase_order_label: str
    received_site_id: str
    received_site_label: str
    supplier_party_id: str
    supplier_label: str
    status: str
    status_label: str
    receipt_date_label: str
    supplier_delivery_reference: str
    received_by_username: str
    notes: str


@dataclass(frozen=True)
class InventoryReceiptLineDesktopDto:
    id: str
    receipt_header_id: str
    purchase_order_line_id: str
    line_number: int
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    quantity_accepted: float
    quantity_accepted_label: str
    quantity_rejected: float
    quantity_rejected_label: str
    uom: str
    unit_cost: float
    unit_cost_label: str
    lot_number: str
    serial_number: str
    expiry_date_label: str
    notes: str


@dataclass(frozen=True)
class InventoryReceiptLineCommand:
    purchase_order_line_id: str
    quantity_accepted: float
    quantity_rejected: float = 0.0
    unit_cost: float | None = None
    lot_number: str = ""
    serial_number: str = ""
    expiry_date: date | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryReceiptPostCommand:
    purchase_order_id: str
    receipt_lines: tuple[InventoryReceiptLineCommand, ...]
    receipt_date: datetime | None = None
    supplier_delivery_reference: str = ""
    notes: str = ""
    receipt_number: str | None = None


def serialize_receipt(
    row,
    *,
    purchase_order_lookup: dict[str, str],
    site_lookup: dict[str, str],
    supplier_lookup: dict[str, str],
) -> InventoryReceiptDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryReceiptDesktopDto(
        id=row.id,
        receipt_number=clean_text(getattr(row, "receipt_number", "")),
        purchase_order_id=clean_text(getattr(row, "purchase_order_id", "")),
        purchase_order_label=purchase_order_lookup.get(
            clean_text(getattr(row, "purchase_order_id", "")),
            "-",
        ),
        received_site_id=clean_text(getattr(row, "received_site_id", "")),
        received_site_label=site_lookup.get(clean_text(getattr(row, "received_site_id", "")), "-"),
        supplier_party_id=clean_text(getattr(row, "supplier_party_id", "")),
        supplier_label=supplier_lookup.get(clean_text(getattr(row, "supplier_party_id", "")), "-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        receipt_date_label=format_datetime(getattr(row, "receipt_date", None)),
        supplier_delivery_reference=clean_text(getattr(row, "supplier_delivery_reference", "")),
        received_by_username=clean_text(getattr(row, "received_by_username", ""), default="-"),
        notes=clean_text(getattr(row, "notes", "")),
    )


def serialize_receipt_line(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryReceiptLineDesktopDto:
    return InventoryReceiptLineDesktopDto(
        id=row.id,
        receipt_header_id=clean_text(getattr(row, "receipt_header_id", "")),
        purchase_order_line_id=clean_text(getattr(row, "purchase_order_line_id", "")),
        line_number=int(getattr(row, "line_number", 0) or 0),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        quantity_accepted=float(getattr(row, "quantity_accepted", 0.0) or 0.0),
        quantity_accepted_label=format_quantity(getattr(row, "quantity_accepted", 0.0)),
        quantity_rejected=float(getattr(row, "quantity_rejected", 0.0) or 0.0),
        quantity_rejected_label=format_quantity(getattr(row, "quantity_rejected", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        unit_cost=float(getattr(row, "unit_cost", 0.0) or 0.0),
        unit_cost_label=format_amount(getattr(row, "unit_cost", 0.0)),
        lot_number=clean_text(getattr(row, "lot_number", "")),
        serial_number=clean_text(getattr(row, "serial_number", "")),
        expiry_date_label=format_date(getattr(row, "expiry_date", None)),
        notes=clean_text(getattr(row, "notes", "")),
    )


__all__ = [
    "InventoryReceiptDesktopDto",
    "InventoryReceiptLineCommand",
    "InventoryReceiptLineDesktopDto",
    "InventoryReceiptPostCommand",
    "serialize_receipt",
    "serialize_receipt_line",
]
