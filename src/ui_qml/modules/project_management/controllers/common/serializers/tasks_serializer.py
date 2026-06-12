from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogOverviewViewModel,
    TaskDetailViewModel,
    TaskExecutionCollectionViewModel,
    TaskRecordViewModel,
)


def serialize_task_catalog_overview_view_model(
    view_model: TaskCatalogOverviewViewModel,
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


def serialize_task_record_view_models(
    view_models: tuple[TaskRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "projectName": str(view_model.state.get("projectName", "") or ""),
            "startDateLabel": str(view_model.state.get("startDateLabel", "") or ""),
            "endDateLabel": str(view_model.state.get("endDateLabel", "") or ""),
            "priorityLabel": str(view_model.state.get("priorityLabel", "") or ""),
            "deadlineLabel": str(view_model.state.get("deadlineLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "progressValue": {
                "value": float(view_model.state.get("percentComplete", "0") or "0") / 100.0,
                "label": view_model.state.get("percentCompleteLabel", "0%"),
            },
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_task_collection_view_model(
    view_model: TaskExecutionCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_task_record_view_models(view_model.items),
    }


def serialize_task_detail_view_model(
    view_model: TaskDetailViewModel,
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
    "serialize_task_catalog_overview_view_model",
    "serialize_task_collection_view_model",
    "serialize_task_detail_view_model",
    "serialize_task_record_view_models",
]
