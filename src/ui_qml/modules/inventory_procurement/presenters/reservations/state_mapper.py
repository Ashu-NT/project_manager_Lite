from __future__ import annotations

from .formatting import can_operate


def build_state(row) -> dict[str, object]:
    operable = can_operate(row)
    return {
        "reservationId": row.id,
        "reservationNumber": row.reservation_number,
        "stockItemId": row.stock_item_id,
        "storeroomId": row.storeroom_id,
        "remainingQty": row.remaining_qty,
        "remainingQtyLabel": row.remaining_qty_label,
        "status": row.status,
        "version": row.version,
        "canIssue": operable,
        "canRelease": operable,
        "canCancel": operable,
        "sourceReferenceType": row.source_reference_type,
        "sourceReferenceId": row.source_reference_id,
    }
