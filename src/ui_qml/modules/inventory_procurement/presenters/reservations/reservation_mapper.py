from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)

from .formatting import build_source_meta, can_operate
from .state_mapper import build_state


def to_record_view_model(row) -> InventoryRecordViewModel:
    operable = can_operate(row)
    return InventoryRecordViewModel(
        id=row.id,
        title=row.reservation_number,
        status_label=row.status_label,
        subtitle=row.stock_item_label,
        supporting_text=(
            f"{row.storeroom_label} | Reserved {row.reserved_qty_label} | Remaining {row.remaining_qty_label}"
        ),
        meta_text=build_source_meta(row),
        can_primary_action=operable,
        can_secondary_action=operable,
        can_tertiary_action=operable,
        state=build_state(row),
    )
