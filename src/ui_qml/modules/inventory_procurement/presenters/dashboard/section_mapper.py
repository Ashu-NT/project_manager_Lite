from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardSectionViewModel,
)

from .row_mapper import to_row_view_model


def to_section_view_model(section) -> InventoryDashboardSectionViewModel:
    return InventoryDashboardSectionViewModel(
        title=section.title,
        subtitle=section.subtitle,
        empty_state=section.empty_state,
        rows=tuple(to_row_view_model(row) for row in section.rows),
    )
