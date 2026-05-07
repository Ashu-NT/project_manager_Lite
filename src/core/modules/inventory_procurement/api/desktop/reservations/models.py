from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class InventoryReservationStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryReservationDesktopDto:
    id: str
    reservation_number: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    reserved_qty: float
    reserved_qty_label: str
    issued_qty: float
    issued_qty_label: str
    remaining_qty: float
    remaining_qty_label: str
    uom: str
    status: str
    status_label: str
    need_by_date: date | None
    need_by_date_label: str
    source_reference_type: str
    source_reference_id: str
    requested_by_username: str
    created_at_label: str
    released_at_label: str
    cancelled_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryReservationCreateCommand:
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    uom: str | None = None
    need_by_date: date | None = None
    source_reference_type: str = ""
    source_reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryReservationIssueCommand:
    reservation_id: str
    quantity: float
    note: str = ""


__all__ = [
    "InventoryReservationCreateCommand",
    "InventoryReservationDesktopDto",
    "InventoryReservationIssueCommand",
    "InventoryReservationStatusDescriptor",
]
