from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
)

from .formatting import build_source_meta
from .state_mapper import build_state


def build_detail(row) -> InventoryDetailViewModel:
    if row is None:
        return InventoryDetailViewModel(
            title="No reservation selected",
            empty_state="Select a reservation to inspect source context, remaining quantity, or launch issue, release, and cancel actions.",
        )
    return InventoryDetailViewModel(
        id=row.id,
        title=row.reservation_number,
        status_label=row.status_label,
        subtitle=f"Requester: {row.requested_by_username or '-'}",
        description=build_source_meta(row),
        fields=(
            InventoryDetailFieldViewModel(
                label="Item",
                value=row.stock_item_label,
            ),
            InventoryDetailFieldViewModel(
                label="Storeroom",
                value=row.storeroom_label,
            ),
            InventoryDetailFieldViewModel(
                label="Quantities",
                value=f"Reserved {row.reserved_qty_label} | Issued {row.issued_qty_label} | Remaining {row.remaining_qty_label}",
            ),
            InventoryDetailFieldViewModel(
                label="Need by",
                value=row.need_by_date_label or "-",
            ),
            InventoryDetailFieldViewModel(
                label="Created / Released / Cancelled",
                value=f"{row.created_at_label or '-'} / {row.released_at_label or '-'} / {row.cancelled_at_label or '-'}",
            ),
            InventoryDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
            InventoryDetailFieldViewModel(
                label="Version",
                value=str(row.version),
            ),
        ),
        state=build_state(row),
    )
