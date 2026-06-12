from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryCatalogViewModel,
    MaintenanceAssetLibraryDetailViewModel,
)


def _serialize_asset_library_catalog(
    view_model: MaintenanceAssetLibraryCatalogViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "subtitle": row.subtitle,
                "statusLabel": row.status_label,
                "supportingText": row.supporting_text,
                "metaText": row.meta_text,
                "canPrimaryAction": bool(row.state.get("canPrimaryAction", False)),
                "canSecondaryAction": bool(row.state.get("canSecondaryAction", False)),
                "canTertiaryAction": False,
                "state": row.state,
            }
            for row in view_model.items
        ],
    }


def _serialize_asset_library_detail(
    view_model: MaintenanceAssetLibraryDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": view_model.state,
    }
