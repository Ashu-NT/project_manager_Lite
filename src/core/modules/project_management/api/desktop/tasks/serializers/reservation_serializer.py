from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.reservation import (
    TaskReservationDesktopDto,
)


def serialize_reservation(reservation) -> TaskReservationDesktopDto:
    status_value = str(
        getattr(getattr(reservation, "status", None), "value", None)
        or getattr(reservation, "status", "")
        or ""
    )
    return TaskReservationDesktopDto(
        id=reservation.id,
        reservation_number=str(getattr(reservation, "reservation_number", "") or ""),
        stock_item_id=str(getattr(reservation, "stock_item_id", "") or ""),
        storeroom_id=str(getattr(reservation, "storeroom_id", "") or ""),
        reserved_qty=float(getattr(reservation, "reserved_qty", 0.0) or 0.0),
        issued_qty=float(getattr(reservation, "issued_qty", 0.0) or 0.0),
        remaining_qty=float(getattr(reservation, "remaining_qty", 0.0) or 0.0),
        uom=str(getattr(reservation, "uom", "") or ""),
        status=status_value,
        status_label=status_value.replace("_", " ").title(),
        need_by_date=getattr(reservation, "need_by_date", None),
        notes=str(getattr(reservation, "notes", "") or ""),
    )


__all__ = ["serialize_reservation"]
