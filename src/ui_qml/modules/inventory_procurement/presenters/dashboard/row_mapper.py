from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardRowViewModel,
)


def to_row_view_model(row) -> InventoryDashboardRowViewModel:
    return InventoryDashboardRowViewModel(
        id=row.id,
        title=row.title,
        subtitle=row.subtitle,
        status_label=row.status_label,
        supporting_text=row.supporting_text,
        meta_text=row.meta_text,
        tone=row.tone,
    )
