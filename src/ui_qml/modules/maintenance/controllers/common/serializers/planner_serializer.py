from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerWorkspaceViewModel,
)

from .selector_serializer import serialize_selector_options


def serialize_planner_workspace_state(
    view_model: MaintenancePlannerWorkspaceViewModel,
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
        "selectedSiteFilter": view_model.selected_site_filter,
        "assetOptions": serialize_selector_options(view_model.asset_options),
        "selectedAssetFilter": view_model.selected_asset_filter,
        "systemOptions": serialize_selector_options(view_model.system_options),
        "selectedSystemFilter": view_model.selected_system_filter,
        "requestQueueOptions": serialize_selector_options(
            view_model.request_queue_options
        ),
        "selectedRequestQueue": view_model.selected_request_queue,
        "workOrderQueueOptions": serialize_selector_options(
            view_model.work_order_queue_options
        ),
        "selectedWorkOrderQueue": view_model.selected_work_order_queue,
        "searchText": view_model.search_text,
        "requestRows": [
            {
                "id": row.id,
                "title": row.request_label,
                "subtitle": row.anchor_label,
                "statusLabel": row.status_label,
                "supportingText": f"Priority: {row.priority_label}",
                "metaText": "",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.request_rows
        ],
        "workOrderRows": [
            {
                "id": row.id,
                "title": row.work_order_label,
                "subtitle": row.work_order_type_label,
                "statusLabel": row.status_label,
                "supportingText": f"Priority: {row.priority_label}",
                "metaText": f"Plan window: {row.plan_window_label}",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.work_order_rows
        ],
        "materialRows": [
            {
                "id": row.id,
                "title": row.material_label,
                "subtitle": row.work_order_label,
                "statusLabel": row.procurement_status_label,
                "supportingText": f"Quantity: {row.quantity_label}",
                "metaText": f"Storeroom: {row.storeroom_label}",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.material_rows
        ],
        "preventiveRows": [
            {
                "id": row.plan_id,
                "title": row.plan_label,
                "subtitle": row.anchor_label,
                "statusLabel": row.due_state_label,
                "supportingText": (
                    f"{row.generation_target_label} | {row.trigger_label}"
                ),
                "metaText": f"Next due: {row.next_due_label} | {row.due_reason}",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {
                    "isDueSoon": row.is_due_soon,
                },
            }
            for row in view_model.preventive_rows
        ],
        "recurringRows": [
            {
                "id": row.anchor_id,
                "title": row.anchor_label,
                "subtitle": row.failure_name,
                "statusLabel": str(row.occurrence_count),
                "supportingText": (
                    f"Lead cause: {row.leading_root_cause_name} | "
                    f"Open work orders: {row.open_work_orders}"
                ),
                "metaText": (
                    f"Open sensor exceptions: {row.sensor_exception_count}"
                ),
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.recurring_rows
        ],
        "emptyState": view_model.empty_state,
    }


__all__ = ["serialize_planner_workspace_state"]
