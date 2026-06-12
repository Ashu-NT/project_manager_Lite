from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)

from .state_mapper import build_category_state


def to_category_record_view_model(category) -> InventoryRecordViewModel:
    state = build_category_state(category)
    usage_bits = []
    if category.is_equipment:
        usage_bits.append("Equipment")
    if category.supports_project_usage:
        usage_bits.append("Projects")
    if category.supports_maintenance_usage:
        usage_bits.append("Maintenance")
    return InventoryRecordViewModel(
        id=category.id,
        title=f"{category.category_code} - {category.name}",
        status_label=category.active_label,
        subtitle=category.category_type_label,
        supporting_text=", ".join(usage_bits) or "Inventory only",
        meta_text=category.description or "",
        can_primary_action=True,
        can_secondary_action=True,
        state=state,
    )
