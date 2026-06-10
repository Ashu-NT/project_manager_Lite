from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDocumentOptionViewModel,
)


def serialize_document_option_view_models(
    view_models: tuple[InventoryDocumentOptionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
            "documentType": view_model.document_type,
            "storageKind": view_model.storage_kind,
            "effectiveDateLabel": view_model.effective_date_label,
            "isActive": view_model.is_active,
        }
        for view_model in view_models
    ]
