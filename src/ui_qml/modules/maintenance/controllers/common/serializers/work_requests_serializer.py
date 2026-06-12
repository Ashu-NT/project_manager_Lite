from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestsWorkspaceViewModel,
)

from .selector_serializer import serialize_selector_options


def serialize_work_request_workspace_state(
    view_model: MaintenanceWorkRequestsWorkspaceViewModel,
) -> dict[str, object]:
    return {
        "overview": {
            "title": view_model.overview.title,
            "subtitle": view_model.overview.subtitle,
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.overview.metrics
            ],
        },
        "siteOptions": serialize_selector_options(view_model.site_options),
        "statusOptions": serialize_selector_options(view_model.status_options),
        "priorityOptions": serialize_selector_options(view_model.priority_options),
        "assetOptions": serialize_selector_options(view_model.asset_options),
        "selectedSiteFilter": view_model.selected_site_filter,
        "selectedStatusFilter": view_model.selected_status_filter,
        "selectedPriorityFilter": view_model.selected_priority_filter,
        "selectedAssetFilter": view_model.selected_asset_filter,
        "searchText": view_model.search_text,
        "workRequests": {
            "title": "Work Requests",
            "subtitle": "Review intake requests, triage state, and conversion-ready backlog before execution planning.",
            "emptyState": view_model.empty_state,
            "items": [
                {
                    "id": row.id,
                    "title": row.title,
                    "subtitle": row.subtitle,
                    "statusLabel": row.status_label,
                    "supportingText": row.supporting_text,
                    "metaText": row.meta_text,
                    "priorityLabel": str(row.state.get("priorityLabel", "") or ""),
                    "assetLabel": str(row.state.get("assetLabel", "") or ""),
                    "locationLabel": str(row.state.get("locationLabel", "") or ""),
                    "requestedAt": str(row.state.get("requestedAt", "") or ""),
                    "requestedByName": str(row.state.get("requestedByName", "") or ""),
                    "canPrimaryAction": bool(
                        row.state.get("canPrimaryAction", False)
                    ),
                    "canSecondaryAction": bool(
                        row.state.get("canSecondaryAction", False)
                    ),
                    "canTertiaryAction": False,
                    "state": row.state,
                }
                for row in view_model.work_requests
            ],
        },
        "selectedWorkRequestId": view_model.selected_work_request_id,
        "selectedWorkRequest": {
            "id": view_model.selected_work_request_detail.id,
            "title": view_model.selected_work_request_detail.title,
            "statusLabel": view_model.selected_work_request_detail.status_label,
            "subtitle": view_model.selected_work_request_detail.subtitle,
            "description": view_model.selected_work_request_detail.description,
            "emptyState": view_model.selected_work_request_detail.empty_state,
            "fields": [
                {
                    "label": field.label,
                    "value": field.value,
                    "supportingText": field.supporting_text,
                }
                for field in view_model.selected_work_request_detail.fields
            ],
            "state": view_model.selected_work_request_detail.state,
        },
        "formSiteOptions": serialize_selector_options(view_model.form_site_options),
        "formLocationOptions": serialize_selector_options(
            view_model.form_location_options
        ),
        "formSystemOptions": serialize_selector_options(view_model.form_system_options),
        "formAssetOptions": serialize_selector_options(view_model.form_asset_options),
        "formComponentOptions": serialize_selector_options(
            view_model.form_component_options
        ),
        "formSourceTypeOptions": serialize_selector_options(
            view_model.form_source_type_options
        ),
        "formPriorityOptions": serialize_selector_options(
            view_model.form_priority_options
        ),
        "formStatusOptions": serialize_selector_options(view_model.form_status_options),
        "emptyState": view_model.empty_state,
    }


__all__ = ["serialize_work_request_workspace_state"]
