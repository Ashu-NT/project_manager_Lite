from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDetailViewModel,
)

from .document_serializer import serialize_document_option_view_models


def serialize_catalog_detail_view_model(
    view_model: InventoryDetailViewModel,
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
        "linkedDocuments": serialize_document_option_view_models(
            view_model.linked_documents
        ),
        "state": dict(view_model.state),
    }
