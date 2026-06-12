from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)

from .state_mapper import build_storeroom_state


def to_storeroom_record_view_model(storeroom) -> InventoryRecordViewModel:
    state = build_storeroom_state(storeroom)
    capabilities = ", ".join(
        bit
        for bit in (
            "Issue" if storeroom.allows_issue else "",
            "Transfer" if storeroom.allows_transfer else "",
            "Receiving" if storeroom.allows_receiving else "",
        )
        if bit
    ) or "No operational permissions"
    return InventoryRecordViewModel(
        id=storeroom.id,
        title=f"{storeroom.storeroom_code} - {storeroom.name}",
        status_label=storeroom.status_label,
        subtitle=storeroom.site_label or "No site",
        supporting_text=capabilities,
        meta_text=storeroom.manager_party_label or storeroom.active_label,
        state=state,
    )
