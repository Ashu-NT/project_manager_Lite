from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_date,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.reservations.models import (
    InventoryReservationDesktopDto,
)


def serialize_reservation(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryReservationDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryReservationDesktopDto(
        id=row.id,
        reservation_number=clean_text(getattr(row, "reservation_number", "")),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(
            clean_text(getattr(row, "stock_item_id", "")),
            "-",
        ),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(
            clean_text(getattr(row, "storeroom_id", "")),
            "-",
        ),
        reserved_qty=float(getattr(row, "reserved_qty", 0.0) or 0.0),
        reserved_qty_label=format_quantity(getattr(row, "reserved_qty", 0.0)),
        issued_qty=float(getattr(row, "issued_qty", 0.0) or 0.0),
        issued_qty_label=format_quantity(getattr(row, "issued_qty", 0.0)),
        remaining_qty=float(getattr(row, "remaining_qty", 0.0) or 0.0),
        remaining_qty_label=format_quantity(getattr(row, "remaining_qty", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        need_by_date=getattr(row, "need_by_date", None),
        need_by_date_label=format_date(getattr(row, "need_by_date", None)),
        source_reference_type=clean_text(getattr(row, "source_reference_type", "")),
        source_reference_id=clean_text(getattr(row, "source_reference_id", "")),
        requested_by_username=clean_text(
            getattr(row, "requested_by_username", ""),
            default="-",
        ),
        created_at_label=format_date(getattr(row, "created_at", None)),
        released_at_label=format_date(getattr(row, "released_at", None)),
        cancelled_at_label=format_date(getattr(row, "cancelled_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


__all__ = ["serialize_reservation"]
