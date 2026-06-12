from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.register import (
    RegisterCollectionViewModel,
    RegisterDetailViewModel,
    RegisterOverviewViewModel,
    RegisterRecordViewModel,
)


def serialize_register_overview_view_model(
    view_model: RegisterOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_register_record_view_models(
    view_models: tuple[RegisterRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "entryCode": str(view_model.state.get("entryCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "ownerName": str(view_model.state.get("ownerName", "")),
            "dueDateLabel": str(view_model.state.get("dueDateLabel", "")),
            "projectName": str(view_model.state.get("projectName", "") or ""),
            "typeLabel": str(view_model.state.get("typeLabel", "") or ""),
            "entryStatus": str(view_model.state.get("statusLabel", "") or ""),
            "severityLabel": str(view_model.state.get("severityLabel", "") or ""),
            "severityValue": {
                "value": float(view_model.state.get("severityScore", "0") or "0") / 100.0,
                "label": view_model.state.get("severityLabel", "—"),
            },
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_register_collection_view_model(
    view_model: RegisterCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_register_record_view_models(view_model.items),
    }


def serialize_register_detail_view_model(
    view_model: RegisterDetailViewModel,
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
        "state": dict(view_model.state),
    }


__all__ = [
    "serialize_register_collection_view_model",
    "serialize_register_detail_view_model",
    "serialize_register_overview_view_model",
    "serialize_register_record_view_models",
]
