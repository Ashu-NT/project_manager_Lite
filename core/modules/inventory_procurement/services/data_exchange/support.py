from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.platform.common.exceptions import ValidationError
from src.core.platform.importing import ImportFieldSpec


ITEM_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="item_code", label="Item Code", required=True),
    ImportFieldSpec(key="name", label="Name", required=True),
    ImportFieldSpec(key="description", label="Description"),
    ImportFieldSpec(key="item_type", label="Item Type"),
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="stock_uom", label="Stock UOM", required=True),
    ImportFieldSpec(key="order_uom", label="Order UOM"),
    ImportFieldSpec(key="issue_uom", label="Issue UOM"),
    ImportFieldSpec(key="order_uom_ratio", label="Order UOM Ratio"),
    ImportFieldSpec(key="issue_uom_ratio", label="Issue UOM Ratio"),
    ImportFieldSpec(key="category_code", label="Category Code"),
    ImportFieldSpec(key="commodity_code", label="Commodity Code"),
    ImportFieldSpec(key="is_stocked", label="Is Stocked"),
    ImportFieldSpec(key="is_purchase_allowed", label="Is Purchase Allowed"),
    ImportFieldSpec(key="default_reorder_policy", label="Default Reorder Policy"),
    ImportFieldSpec(key="min_qty", label="Minimum Quantity"),
    ImportFieldSpec(key="max_qty", label="Maximum Quantity"),
    ImportFieldSpec(key="reorder_point", label="Reorder Point"),
    ImportFieldSpec(key="reorder_qty", label="Reorder Quantity"),
    ImportFieldSpec(key="lead_time_days", label="Lead Time Days"),
    ImportFieldSpec(key="is_lot_tracked", label="Lot Tracked"),
    ImportFieldSpec(key="is_serial_tracked", label="Serial Tracked"),
    ImportFieldSpec(key="shelf_life_days", label="Shelf Life Days"),
    ImportFieldSpec(key="preferred_party_code", label="Preferred Party Code"),
    ImportFieldSpec(key="notes", label="Notes"),
)

STOREROOM_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="storeroom_code", label="Storeroom Code", required=True),
    ImportFieldSpec(key="name", label="Name", required=True),
    ImportFieldSpec(key="site_code", label="Site Code", required=True),
    ImportFieldSpec(key="description", label="Description"),
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="storeroom_type", label="Storeroom Type"),
    ImportFieldSpec(key="is_internal_supplier", label="Is Internal Supplier"),
    ImportFieldSpec(key="allows_issue", label="Allows Issue"),
    ImportFieldSpec(key="allows_transfer", label="Allows Transfer"),
    ImportFieldSpec(key="allows_receiving", label="Allows Receiving"),
    ImportFieldSpec(key="requires_reservation_for_issue", label="Requires Reservation For Issue"),
    ImportFieldSpec(key="requires_supplier_reference_for_receipt", label="Requires Supplier Reference For Receipt"),
    ImportFieldSpec(key="default_currency_code", label="Default Currency Code"),
    ImportFieldSpec(key="manager_party_code", label="Manager Party Code"),
    ImportFieldSpec(key="notes", label="Notes"),
)

REQUISITION_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="requisition_number", label="Requisition Number", required=True),
    ImportFieldSpec(key="requesting_site_code", label="Requesting Site Code", required=True),
    ImportFieldSpec(key="requesting_storeroom_code", label="Requesting Storeroom Code", required=True),
    ImportFieldSpec(key="purpose", label="Purpose"),
    ImportFieldSpec(key="needed_by_date", label="Needed By Date"),
    ImportFieldSpec(key="priority", label="Priority"),
    ImportFieldSpec(key="source_reference_type", label="Source Reference Type"),
    ImportFieldSpec(key="source_reference_id", label="Source Reference ID"),
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="header_notes", label="Header Notes"),
    ImportFieldSpec(key="line_number", label="Line Number", required=True),
    ImportFieldSpec(key="item_code", label="Item Code", required=True),
    ImportFieldSpec(key="line_description", label="Line Description"),
    ImportFieldSpec(key="quantity_requested", label="Quantity Requested", required=True),
    ImportFieldSpec(key="uom", label="UOM"),
    ImportFieldSpec(key="line_needed_by_date", label="Line Needed By Date"),
    ImportFieldSpec(key="estimated_unit_cost", label="Estimated Unit Cost"),
    ImportFieldSpec(key="suggested_supplier_code", label="Suggested Supplier Code"),
    ImportFieldSpec(key="line_notes", label="Line Notes"),
)

PURCHASE_ORDER_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="po_number", label="PO Number", required=True),
    ImportFieldSpec(key="site_code", label="Site Code", required=True),
    ImportFieldSpec(key="supplier_code", label="Supplier Code", required=True),
    ImportFieldSpec(key="currency_code", label="Currency Code"),
    ImportFieldSpec(key="source_requisition_number", label="Source Requisition Number"),
    ImportFieldSpec(key="order_date", label="Order Date"),
    ImportFieldSpec(key="expected_delivery_date", label="Expected Delivery Date"),
    ImportFieldSpec(key="supplier_reference", label="Supplier Reference"),
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="header_notes", label="Header Notes"),
    ImportFieldSpec(key="line_number", label="Line Number", required=True),
    ImportFieldSpec(key="item_code", label="Item Code", required=True),
    ImportFieldSpec(key="destination_storeroom_code", label="Destination Storeroom Code", required=True),
    ImportFieldSpec(key="line_description", label="Line Description"),
    ImportFieldSpec(key="quantity_ordered", label="Quantity Ordered", required=True),
    ImportFieldSpec(key="uom", label="UOM"),
    ImportFieldSpec(key="unit_price", label="Unit Price"),
    ImportFieldSpec(key="line_expected_delivery_date", label="Line Expected Delivery Date"),
    ImportFieldSpec(key="source_requisition_line_ref", label="Source Requisition Line Ref"),
    ImportFieldSpec(key="line_notes", label="Line Notes"),
)

RECEIPT_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="receipt_number", label="Receipt Number", required=True),
    ImportFieldSpec(key="purchase_order_number", label="Purchase Order Number", required=True),
    ImportFieldSpec(key="receipt_date", label="Receipt Date"),
    ImportFieldSpec(key="supplier_delivery_reference", label="Supplier Delivery Reference"),
    ImportFieldSpec(key="header_notes", label="Header Notes"),
    ImportFieldSpec(key="line_number", label="Line Number", required=True),
    ImportFieldSpec(key="purchase_order_line_number", label="Purchase Order Line Number", required=True),
    ImportFieldSpec(key="quantity_accepted", label="Quantity Accepted", required=True),
    ImportFieldSpec(key="quantity_rejected", label="Quantity Rejected"),
    ImportFieldSpec(key="unit_cost", label="Unit Cost"),
    ImportFieldSpec(key="lot_number", label="Lot Number"),
    ImportFieldSpec(key="serial_number", label="Serial Number"),
    ImportFieldSpec(key="expiry_date", label="Expiry Date"),
    ImportFieldSpec(key="line_notes", label="Line Notes"),
)

ITEM_EXPORT_FIELDS: tuple[str, ...] = tuple(field.key for field in ITEM_FIELDS)
STOREROOM_EXPORT_FIELDS: tuple[str, ...] = tuple(field.key for field in STOREROOM_FIELDS)
REQUISITION_EXPORT_FIELDS: tuple[str, ...] = (
    "requisition_number",
    "status",
    "requesting_site_code",
    "requesting_storeroom_code",
    "requester_username",
    "needed_by_date",
    "priority",
    "approval_request_id",
    "source_reference_type",
    "source_reference_id",
    "submitted_at",
    "approved_at",
    "cancelled_at",
    "purpose",
    "line_number",
    "item_code",
    "line_description",
    "quantity_requested",
    "uom",
    "line_needed_by_date",
    "estimated_unit_cost",
    "quantity_sourced",
    "suggested_supplier_code",
    "line_status",
    "line_notes",
    "header_notes",
)
PURCHASE_ORDER_EXPORT_FIELDS: tuple[str, ...] = (
    "po_number",
    "status",
    "site_code",
    "supplier_code",
    "order_date",
    "expected_delivery_date",
    "currency_code",
    "approval_request_id",
    "source_requisition_number",
    "supplier_reference",
    "submitted_at",
    "approved_at",
    "sent_at",
    "closed_at",
    "cancelled_at",
    "line_number",
    "item_code",
    "destination_storeroom_code",
    "line_description",
    "quantity_ordered",
    "quantity_received",
    "quantity_rejected",
    "uom",
    "unit_price",
    "line_expected_delivery_date",
    "source_requisition_line_ref",
    "line_status",
    "line_notes",
    "header_notes",
)
RECEIPT_EXPORT_FIELDS: tuple[str, ...] = (
    "receipt_number",
    "purchase_order_number",
    "received_site_code",
    "supplier_code",
    "status",
    "receipt_date",
    "supplier_delivery_reference",
    "received_by_username",
    "line_number",
    "purchase_order_line_number",
    "item_code",
    "storeroom_code",
    "quantity_accepted",
    "quantity_rejected",
    "uom",
    "unit_cost",
    "lot_number",
    "serial_number",
    "expiry_date",
    "line_notes",
    "header_notes",
)


@dataclass(frozen=True)
class InventoryExportRequest:
    output_path: Path
    active_only: bool | None = None
    status: str | None = None
    site_id: str | None = None
    storeroom_id: str | None = None
    supplier_party_id: str | None = None
    purchase_order_id: str | None = None
    limit: int = 200


def text(value: str | None) -> str:
    return str(value or "").strip()


def optional_text(value: str | None) -> str | None:
    normalized = text(value)
    return normalized or None


def stringify_bool(value: bool) -> str:
    return "true" if bool(value) else "false"


def enum_value(value: object) -> str:
    return str(getattr(value, "value", value) or "")


def isoformat(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


def parse_optional_bool(value: str | None) -> bool | None:
    normalized = text(value).lower()
    if not normalized:
        return None
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValidationError(
        "Boolean fields must use true/false or yes/no tokens.",
        code="INVENTORY_IMPORT_BOOLEAN_INVALID",
    )


def parse_optional_float(value: str | None, *, label: str) -> float | None:
    normalized = text(value)
    if not normalized:
        return None
    try:
        return float(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{label} must be a number.",
            code="INVENTORY_IMPORT_NUMBER_INVALID",
        ) from exc


def parse_optional_int(value: str | None, *, label: str) -> int | None:
    normalized = text(value)
    if not normalized:
        return None
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{label} must be a whole number.",
            code="INVENTORY_IMPORT_INTEGER_INVALID",
        ) from exc


def parse_optional_date(value: str | None, *, label: str) -> date | None:
    normalized = text(value)
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{label} must use ISO date format YYYY-MM-DD.",
            code="INVENTORY_IMPORT_DATE_INVALID",
        ) from exc


def write_rows(output_path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


__all__ = [
    "ITEM_EXPORT_FIELDS",
    "ITEM_FIELDS",
    "InventoryExportRequest",
    "PURCHASE_ORDER_EXPORT_FIELDS",
    "PURCHASE_ORDER_FIELDS",
    "RECEIPT_EXPORT_FIELDS",
    "RECEIPT_FIELDS",
    "REQUISITION_EXPORT_FIELDS",
    "REQUISITION_FIELDS",
    "STOREROOM_EXPORT_FIELDS",
    "STOREROOM_FIELDS",
    "enum_value",
    "isoformat",
    "optional_text",
    "parse_optional_bool",
    "parse_optional_date",
    "parse_optional_float",
    "parse_optional_int",
    "stringify_bool",
    "text",
    "write_rows",
]
