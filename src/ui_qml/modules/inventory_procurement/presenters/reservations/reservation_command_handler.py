from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryReservationCreateCommand,
    InventoryReservationIssueCommand,
)

from .validation import (
    optional_date,
    optional_text,
    require_positive_float,
    require_text,
)


def create_reservation(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryReservationCreateCommand(
        stock_item_id=require_text(payload, "stockItemId", "Choose an item before saving."),
        storeroom_id=require_text(payload, "storeroomId", "Choose a storeroom before saving."),
        reserved_qty=require_positive_float(
            payload, "reservedQty", "Reserved quantity must be greater than zero."
        ),
        need_by_date=optional_date(payload, "needByDate"),
        source_reference_type=optional_text(payload, "sourceReferenceType") or "",
        source_reference_id=optional_text(payload, "sourceReferenceId") or "",
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_reservation(command)


def issue_reservation(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryReservationIssueCommand(
        reservation_id=require_text(
            payload,
            "reservationId",
            "Reservation ID is required before issuing stock.",
        ),
        quantity=require_positive_float(
            payload, "quantity", "Issue quantity must be greater than zero."
        ),
        note=optional_text(payload, "note") or "",
    )
    desktop_api.issue_reserved_stock(command)


def release_reservation(desktop_api, reservation_id: str, note: str = "") -> None:
    normalized_id = (reservation_id or "").strip()
    if not normalized_id:
        raise ValueError("Reservation ID is required before releasing stock.")
    desktop_api.release_reservation(normalized_id, note=note)


def cancel_reservation(desktop_api, reservation_id: str, note: str = "") -> None:
    normalized_id = (reservation_id or "").strip()
    if not normalized_id:
        raise ValueError("Reservation ID is required before cancelling stock.")
    desktop_api.cancel_reservation(normalized_id, note=note)
