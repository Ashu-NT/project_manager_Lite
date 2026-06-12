from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)

_RESERVED_ROW_KEYS: frozenset[str] = frozenset({
    "id", "title", "statusLabel", "subtitle", "supportingText",
    "metaText", "canPrimaryAction", "canSecondaryAction",
    "canTertiaryAction", "state",
})


def serialize_record_view_models(
    view_models: tuple[InventoryRecordViewModel, ...],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for view_model in view_models:
        state = dict(view_model.state)
        row: dict[str, object] = {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": state,
        }
        for key, value in state.items():
            if key not in _RESERVED_ROW_KEYS:
                row[key] = value
        rows.append(row)
    return rows
