from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)

from .state_mapper import build_balance_state


def to_balance_record_view_model(balance) -> InventoryRecordViewModel:
    state = build_balance_state(balance)
    return InventoryRecordViewModel(
        id=balance.id,
        title=balance.stock_item_label or balance.stock_item_id,
        status_label="Reorder" if balance.reorder_required else "Healthy",
        subtitle=balance.storeroom_label or balance.storeroom_id,
        supporting_text=(
            f"On hand {balance.on_hand_qty_label} | Available {balance.available_qty_label} | Reserved {balance.reserved_qty_label}"
        ),
        meta_text=f"Avg cost {balance.average_cost_label} | UOM {balance.uom or '-'}",
        can_tertiary_action=True,
        state=state,
    )
