from __future__ import annotations

from datetime import date, datetime

from core.modules.inventory_procurement.domain import (
    PurchaseOrder,
    PurchaseRequisition,
    StockItem,
    Storeroom,
)


def build_item_lookup(rows: list[StockItem]) -> dict[str, StockItem]:
    return {row.id: row for row in rows}


def build_storeroom_lookup(rows: list[Storeroom]) -> dict[str, Storeroom]:
    return {row.id: row for row in rows}


def build_requisition_lookup(rows: list[PurchaseRequisition]) -> dict[str, PurchaseRequisition]:
    return {row.id: row for row in rows}


def build_purchase_order_lookup(rows: list[PurchaseOrder]) -> dict[str, PurchaseOrder]:
    return {row.id: row for row in rows}


def format_item_label(item_id: str | None, item_lookup: dict[str, StockItem]) -> str:
    if not item_id:
        return "-"
    item = item_lookup.get(item_id)
    if item is None:
        return item_id
    return f"{item.item_code} - {item.name}"


def format_storeroom_label(storeroom_id: str | None, storeroom_lookup: dict[str, Storeroom]) -> str:
    if not storeroom_id:
        return "-"
    storeroom = storeroom_lookup.get(storeroom_id)
    if storeroom is None:
        return storeroom_id
    return f"{storeroom.storeroom_code} - {storeroom.name}"


def format_requisition_label(
    requisition_id: str | None,
    requisition_lookup: dict[str, PurchaseRequisition],
) -> str:
    if not requisition_id:
        return "-"
    requisition = requisition_lookup.get(requisition_id)
    if requisition is None:
        return requisition_id
    return requisition.requisition_number


def format_purchase_order_label(
    purchase_order_id: str | None,
    purchase_order_lookup: dict[str, PurchaseOrder],
) -> str:
    if not purchase_order_id:
        return "-"
    purchase_order = purchase_order_lookup.get(purchase_order_id)
    if purchase_order is None:
        return purchase_order_id
    return purchase_order.po_number


def humanize_status(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "-"
    return normalized.replace("_", " ").title()


def format_date(value: date | None) -> str:
    if value is None:
        return "-"
    return value.isoformat()


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def format_quantity(value: float | int | None) -> str:
    return f"{float(value or 0.0):,.3f}"


__all__ = [
    "build_item_lookup",
    "build_purchase_order_lookup",
    "build_requisition_lookup",
    "build_storeroom_lookup",
    "format_date",
    "format_datetime",
    "format_item_label",
    "format_purchase_order_label",
    "format_quantity",
    "format_requisition_label",
    "format_storeroom_label",
    "humanize_status",
]
