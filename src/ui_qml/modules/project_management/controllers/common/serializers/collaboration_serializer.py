from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationContextViewModel,
    CollaborationDetailViewModel,
    CollaborationOverviewViewModel,
    CollaborationPanelTabViewModel,
    CollaborationRecordViewModel,
)


def serialize_collaboration_overview_view_model(
    view_model: CollaborationOverviewViewModel,
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


def serialize_collaboration_record_view_models(
    view_models: tuple[CollaborationRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "routeId": str(view_model.state.get("routeId", "")),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_collaboration_collection_view_model(
    view_model: CollaborationCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_collaboration_record_view_models(view_model.items),
    }


def serialize_collaboration_context_view_model(
    view_model: CollaborationContextViewModel,
) -> dict[str, object]:
    return {
        "projectOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.project_options
        ],
        "teamOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.team_options
        ],
        "periodOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.period_options
        ],
        "unreadOptions": [
            {"value": option.value, "label": option.label}
            for option in view_model.unread_options
        ],
    }


def serialize_collaboration_panel_tab_view_models(
    view_models: tuple[CollaborationPanelTabViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "label": view_model.label,
            "count": view_model.count,
        }
        for view_model in view_models
    ]


def serialize_collaboration_detail_view_model(
    view_model: CollaborationDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "state": dict(view_model.state),
        "fields": [
            {
                "label": field.label,
                "value": field.value,
            }
            for field in view_model.fields
        ],
        "activity": serialize_collaboration_collection_view_model(view_model.activity),
        "relatedItems": serialize_collaboration_collection_view_model(
            view_model.related_items
        ),
        "audit": serialize_collaboration_collection_view_model(view_model.audit),
    }


__all__ = [
    "serialize_collaboration_collection_view_model",
    "serialize_collaboration_context_view_model",
    "serialize_collaboration_detail_view_model",
    "serialize_collaboration_overview_view_model",
    "serialize_collaboration_panel_tab_view_models",
    "serialize_collaboration_record_view_models",
]
