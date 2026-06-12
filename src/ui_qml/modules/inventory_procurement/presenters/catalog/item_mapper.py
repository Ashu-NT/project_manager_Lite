from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)

from .state_mapper import build_item_state


def to_item_record_view_model(item) -> InventoryRecordViewModel:
    state = build_item_state(item)
    return InventoryRecordViewModel(
        id=item.id,
        title=f"{item.item_code} - {item.name}",
        status_label=item.active_label,
        subtitle=item.category_label or "Uncategorized",
        supporting_text=(
            f"{item.status_label} | Stock UOM {item.stock_uom or '-'} | "
            f"ROP {item.reorder_point_label} | ROQ {item.reorder_qty_label}"
        ),
        meta_text=(
            item.preferred_party_label
            if item.preferred_party_id
            else "No preferred supplier linked"
        ),
        can_primary_action=True,
        can_secondary_action=True,
        state=state,
    )
