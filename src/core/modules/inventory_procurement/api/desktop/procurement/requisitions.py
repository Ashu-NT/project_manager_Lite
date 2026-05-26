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
class InventoryRequisitionDesktopDto:
    id: str
    requisition_number: str
    requesting_site_id: str
    requesting_site_label: str
    requesting_storeroom_id: str
    requesting_storeroom_label: str
    requester_username: str
    status: str
    status_label: str
    purpose: str
    needed_by_date: date | None
    needed_by_date_label: str
    priority: str
    approval_request_id: str | None
    source_reference_type: str
    source_reference_id: str
    source_module: str
    source_entity_type: str
    source_code_snapshot: str
    source_title_snapshot: str
    source_status_snapshot: str
    submitted_at_label: str
    approved_at_label: str
    cancelled_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryRequisitionLineDesktopDto:
    id: str
    purchase_requisition_id: str
    line_number: int
    stock_item_id: str
    stock_item_label: str
    description: str
    quantity_requested: float
    quantity_requested_label: str
    uom: str
    needed_by_date: date | None
    needed_by_date_label: str
    estimated_unit_cost: float
    estimated_unit_cost_label: str
    quantity_sourced: float
    quantity_sourced_label: str
    suggested_supplier_party_id: str | None
    suggested_supplier_label: str
    status: str
    status_label: str
    notes: str


@dataclass(frozen=True)
class InventoryRequisitionCreateCommand:
    requesting_site_id: str
    requesting_storeroom_id: str
    purpose: str = ""
    needed_by_date: date | None = None
    priority: str = "NORMAL"
    source_reference_type: str = ""
    source_reference_id: str = ""
    source_module: str = ""
    source_entity_type: str = ""
    source_code_snapshot: str = ""
    source_title_snapshot: str = ""
    source_status_snapshot: str = ""
    notes: str = ""
    requisition_number: str | None = None


@dataclass(frozen=True)
class InventoryRequisitionUpdateCommand:
    requisition_id: str
    requesting_site_id: str
    requesting_storeroom_id: str
    purpose: str = ""
    needed_by_date: date | None = None
    priority: str = "NORMAL"
    source_reference_type: str = ""
    source_reference_id: str = ""
    source_module: str = ""
    source_entity_type: str = ""
    source_code_snapshot: str = ""
    source_title_snapshot: str = ""
    source_status_snapshot: str = ""
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryRequisitionLineCreateCommand:
    requisition_id: str
    stock_item_id: str
    quantity_requested: float
    uom: str | None = None
    description: str = ""
    needed_by_date: date | None = None
    estimated_unit_cost: float = 0.0
    suggested_supplier_party_id: str | None = None
    notes: str = ""


def serialize_requisition(
    row,
    *,
    site_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
    requisition_lookup: dict[str, str],
) -> InventoryRequisitionDesktopDto:
    del requisition_lookup
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryRequisitionDesktopDto(
        id=row.id,
        requisition_number=clean_text(getattr(row, "requisition_number", "")),
        requesting_site_id=clean_text(getattr(row, "requesting_site_id", "")),
        requesting_site_label=site_lookup.get(
            clean_text(getattr(row, "requesting_site_id", "")),
            "-",
        ),
        requesting_storeroom_id=clean_text(getattr(row, "requesting_storeroom_id", "")),
        requesting_storeroom_label=storeroom_lookup.get(
            clean_text(getattr(row, "requesting_storeroom_id", "")),
            "-",
        ),
        requester_username=clean_text(getattr(row, "requester_username", ""), default="-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        purpose=clean_text(getattr(row, "purpose", "")),
        needed_by_date=getattr(row, "needed_by_date", None),
        needed_by_date_label=format_date(getattr(row, "needed_by_date", None)),
        priority=clean_text(getattr(row, "priority", "")),
        approval_request_id=clean_text(getattr(row, "approval_request_id", "")) or None,
        source_reference_type=clean_text(getattr(row, "source_reference_type", "")),
        source_reference_id=clean_text(getattr(row, "source_reference_id", "")),
        source_module=clean_text(getattr(row, "source_module", "")),
        source_entity_type=clean_text(getattr(row, "source_entity_type", "")),
        source_code_snapshot=clean_text(getattr(row, "source_code_snapshot", "")),
        source_title_snapshot=clean_text(getattr(row, "source_title_snapshot", "")),
        source_status_snapshot=clean_text(getattr(row, "source_status_snapshot", "")),
        submitted_at_label=format_datetime(getattr(row, "submitted_at", None)),
        approved_at_label=format_datetime(getattr(row, "approved_at", None)),
        cancelled_at_label=format_datetime(getattr(row, "cancelled_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_requisition_line(
    row,
    *,
    item_lookup: dict[str, str],
    supplier_lookup: dict[str, str],
) -> InventoryRequisitionLineDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    supplier_id = clean_text(getattr(row, "suggested_supplier_party_id", "")) or None
    return InventoryRequisitionLineDesktopDto(
        id=row.id,
        purchase_requisition_id=clean_text(getattr(row, "purchase_requisition_id", "")),
        line_number=int(getattr(row, "line_number", 0) or 0),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        description=clean_text(getattr(row, "description", "")),
        quantity_requested=float(getattr(row, "quantity_requested", 0.0) or 0.0),
        quantity_requested_label=format_quantity(getattr(row, "quantity_requested", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        needed_by_date=getattr(row, "needed_by_date", None),
        needed_by_date_label=format_date(getattr(row, "needed_by_date", None)),
        estimated_unit_cost=float(getattr(row, "estimated_unit_cost", 0.0) or 0.0),
        estimated_unit_cost_label=format_amount(getattr(row, "estimated_unit_cost", 0.0)),
        quantity_sourced=float(getattr(row, "quantity_sourced", 0.0) or 0.0),
        quantity_sourced_label=format_quantity(getattr(row, "quantity_sourced", 0.0)),
        suggested_supplier_party_id=supplier_id,
        suggested_supplier_label=supplier_lookup.get(supplier_id or "", "-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        notes=clean_text(getattr(row, "notes", "")),
    )


__all__ = [
    "InventoryRequisitionCreateCommand",
    "InventoryRequisitionDesktopDto",
    "InventoryRequisitionLineCreateCommand",
    "InventoryRequisitionLineDesktopDto",
    "InventoryRequisitionUpdateCommand",
    "serialize_requisition",
    "serialize_requisition_line",
]
