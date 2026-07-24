from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogOverviewViewModel,
    ProjectDetailViewModel,
    ProjectRecordViewModel,
)


def serialize_project_catalog_overview_view_model(
    view_model: ProjectCatalogOverviewViewModel,
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


def serialize_project_record_view_models(
    view_models: tuple[ProjectRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "projectCode": str(view_model.state.get("projectCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "clientName": str(view_model.state.get("clientName", "") or ""),
            "clientContact": str(view_model.state.get("clientContact", "") or ""),
            "siteLabel": str(view_model.state.get("siteLabel", "") or ""),
            "startDateLabel": str(view_model.state.get("startDateLabel", "") or ""),
            "endDateLabel": str(view_model.state.get("endDateLabel", "") or ""),
            "plannedBudgetLabel": str(view_model.state.get("plannedBudgetLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_project_detail_view_model(
    view_model: ProjectDetailViewModel,
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
    "serialize_project_catalog_overview_view_model",
    "serialize_project_detail_view_model",
    "serialize_project_record_view_models",
]
