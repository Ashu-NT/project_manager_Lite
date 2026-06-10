from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)


def to_record_view_model(row) -> InventoryRecordViewModel:
    return InventoryRecordViewModel(
        id=row.id,
        title=row.title,
        status_label=row.status_label,
        subtitle=row.subtitle,
        supporting_text=row.supporting_text,
        meta_text=row.meta_text,
        can_primary_action=False,
        can_secondary_action=False,
        can_tertiary_action=False,
    )
