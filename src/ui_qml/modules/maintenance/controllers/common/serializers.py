from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryCatalogViewModel,
    MaintenanceAssetLibraryDetailViewModel,
    MaintenanceAssetsWorkspaceViewModel,
)
from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardWorkspaceViewModel,
)
from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerWorkspaceViewModel,
)
from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityWorkspaceViewModel,
)
from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrdersWorkspaceViewModel,
)
from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestsWorkspaceViewModel,
)
from src.ui_qml.modules.maintenance.view_models.workspace import (
    MaintenanceWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: MaintenanceWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }


def serialize_selector_options(view_models) -> list[dict[str, object]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
        }
        for view_model in view_models
    ]


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


def serialize_assets_workspace_state(
    view_model: MaintenanceAssetsWorkspaceViewModel,
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
        "activeFilterOptions": serialize_selector_options(
            view_model.active_filter_options
        ),
        "selectedSiteFilter": view_model.selected_site_filter,
        "selectedActiveFilter": view_model.selected_active_filter,
        "searchText": view_model.search_text,
        "locations": _serialize_asset_library_catalog(view_model.locations),
        "systems": _serialize_asset_library_catalog(view_model.systems),
        "assets": _serialize_asset_library_catalog(view_model.assets),
        "components": _serialize_asset_library_catalog(view_model.components),
        "selectedLocationId": view_model.selected_location_id,
        "selectedSystemId": view_model.selected_system_id,
        "selectedAssetId": view_model.selected_asset_id,
        "selectedComponentId": view_model.selected_component_id,
        "selectedLocation": _serialize_asset_library_detail(
            view_model.selected_location_detail
        ),
        "selectedSystem": _serialize_asset_library_detail(
            view_model.selected_system_detail
        ),
        "selectedAsset": _serialize_asset_library_detail(
            view_model.selected_asset_detail
        ),
        "selectedComponent": _serialize_asset_library_detail(
            view_model.selected_component_detail
        ),
        "formSiteOptions": serialize_selector_options(view_model.form_site_options),
        "formLocationOptions": serialize_selector_options(
            view_model.form_location_options
        ),
        "formParentLocationOptions": serialize_selector_options(
            view_model.form_parent_location_options
        ),
        "formSystemOptions": serialize_selector_options(view_model.form_system_options),
        "formParentSystemOptions": serialize_selector_options(
            view_model.form_parent_system_options
        ),
        "formAssetOptions": serialize_selector_options(view_model.form_asset_options),
        "formParentAssetOptions": serialize_selector_options(
            view_model.form_parent_asset_options
        ),
        "formComponentOptions": serialize_selector_options(
            view_model.form_component_options
        ),
        "formParentComponentOptions": serialize_selector_options(
            view_model.form_parent_component_options
        ),
        "formStatusOptions": serialize_selector_options(view_model.form_status_options),
        "formCriticalityOptions": serialize_selector_options(
            view_model.form_criticality_options
        ),
        "formManufacturerOptions": serialize_selector_options(
            view_model.form_manufacturer_options
        ),
        "formSupplierOptions": serialize_selector_options(
            view_model.form_supplier_options
        ),
        "emptyState": view_model.empty_state,
    }


def serialize_dashboard_workspace_state(
    view_model: MaintenanceDashboardWorkspaceViewModel,
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
        "locationOptions": serialize_selector_options(view_model.location_options),
        "selectedLocationFilter": view_model.selected_location_filter,
        "windowOptions": serialize_selector_options(view_model.window_options),
        "selectedDaysFilter": view_model.selected_days_filter,
        "backlogRows": [
            {
                "id": f"{row.group}:{row.label}",
                "title": row.label,
                "subtitle": row.group.title(),
                "statusLabel": row.value,
                "supportingText": "Current dashboard metric",
                "metaText": "",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.backlog_rows
        ],
        "rootCauseRows": [
            {
                "id": f"{row.failure_name}:{row.root_cause_name}",
                "title": row.failure_name,
                "subtitle": row.root_cause_name,
                "statusLabel": str(row.work_order_count),
                "supportingText": (
                    f"Downtime minutes: {row.total_downtime_minutes} | "
                    f"Open work orders: {row.open_work_orders}"
                ),
                "metaText": f"Latest occurrence: {row.latest_occurrence_at_label}",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.root_cause_rows
        ],
        "recurringRows": [
            {
                "id": f"{row.anchor_label}:{row.failure_name}",
                "title": row.anchor_label,
                "subtitle": row.failure_name,
                "statusLabel": str(row.occurrence_count),
                "supportingText": (
                    f"Lead cause: {row.leading_root_cause_name or '-'} | "
                    f"Open work orders: {row.open_work_orders}"
                ),
                "metaText": (
                    f"Downtime minutes: {row.total_downtime_minutes} | "
                    f"Mean interval: {row.mean_interval_hours_label}"
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


def serialize_reliability_workspace_state(
    view_model: MaintenanceReliabilityWorkspaceViewModel,
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
        "locationOptions": serialize_selector_options(view_model.location_options),
        "selectedLocationFilter": view_model.selected_location_filter,
        "failureSymptomOptions": [
            {
                "value": view_model_option.value,
                "label": view_model_option.label,
                "failureCode": view_model_option.failure_code,
                "name": view_model_option.name,
                "isActive": view_model_option.is_active,
            }
            for view_model_option in view_model.failure_symptom_options
        ],
        "selectedFailureCodeFilter": view_model.selected_failure_code_filter,
        "daysOptions": serialize_selector_options(view_model.days_options),
        "selectedDaysFilter": view_model.selected_days_filter,
        "limitOptions": serialize_selector_options(view_model.limit_options),
        "selectedLimitFilter": view_model.selected_limit_filter,
        "thresholdOptions": serialize_selector_options(view_model.threshold_options),
        "selectedThresholdFilter": view_model.selected_threshold_filter,
        "suggestionRows": [
            {
                "id": f"{row.match_scope_label}:{row.root_cause_name}",
                "title": row.root_cause_name,
                "subtitle": row.match_scope_label,
                "statusLabel": str(row.occurrence_count),
                "supportingText": f"Downtime minutes: {row.total_downtime_minutes}",
                "metaText": f"Latest occurrence: {row.latest_occurrence_at_label}",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.suggestion_rows
        ],
        "rootCauseRows": [
            {
                "id": f"{row.failure_name}:{row.root_cause_name}",
                "title": row.failure_name,
                "subtitle": row.root_cause_name,
                "statusLabel": str(row.work_order_count),
                "supportingText": (
                    f"Downtime minutes: {row.total_downtime_minutes} | "
                    f"Open work orders: {row.open_work_orders}"
                ),
                "metaText": "",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.root_cause_rows
        ],
        "recurringRows": [
            {
                "id": f"{row.anchor_label}:{row.failure_name}",
                "title": row.anchor_label,
                "subtitle": row.failure_name,
                "statusLabel": str(row.occurrence_count),
                "supportingText": (
                    f"Lead cause: {row.leading_root_cause_name or '-'} | "
                    f"Open work orders: {row.open_work_orders}"
                ),
                "metaText": f"Mean interval: {row.mean_interval_hours_label}",
                "canPrimaryAction": False,
                "canSecondaryAction": False,
                "canTertiaryAction": False,
                "state": {},
            }
            for row in view_model.recurring_rows
        ],
        "emptyState": view_model.empty_state,
    }


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


def serialize_work_order_workspace_state(
    view_model: MaintenanceWorkOrdersWorkspaceViewModel,
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
        "workOrderTypeOptions": serialize_selector_options(
            view_model.work_order_type_options
        ),
        "assetOptions": serialize_selector_options(view_model.asset_options),
        "selectedSiteFilter": view_model.selected_site_filter,
        "selectedStatusFilter": view_model.selected_status_filter,
        "selectedPriorityFilter": view_model.selected_priority_filter,
        "selectedWorkOrderTypeFilter": view_model.selected_work_order_type_filter,
        "selectedAssetFilter": view_model.selected_asset_filter,
        "searchText": view_model.search_text,
        "workOrders": {
            "title": "Work Orders",
            "subtitle": "Review execution records, planning state, and lifecycle readiness before detailed execution handling.",
            "emptyState": view_model.empty_state,
            "items": [
                {
                    "id": row.id,
                    "title": row.title,
                    "subtitle": row.subtitle,
                    "statusLabel": row.status_label,
                    "supportingText": row.supporting_text,
                    "metaText": row.meta_text,
                    "canPrimaryAction": bool(
                        row.state.get("canPrimaryAction", False)
                    ),
                    "canSecondaryAction": bool(
                        row.state.get("canSecondaryAction", False)
                    ),
                    "canTertiaryAction": False,
                    "state": row.state,
                }
                for row in view_model.work_orders
            ],
        },
        "selectedWorkOrderId": view_model.selected_work_order_id,
        "selectedWorkOrder": {
            "id": view_model.selected_work_order_detail.id,
            "title": view_model.selected_work_order_detail.title,
            "statusLabel": view_model.selected_work_order_detail.status_label,
            "subtitle": view_model.selected_work_order_detail.subtitle,
            "description": view_model.selected_work_order_detail.description,
            "emptyState": view_model.selected_work_order_detail.empty_state,
            "fields": [
                {
                    "label": field.label,
                    "value": field.value,
                    "supportingText": field.supporting_text,
                }
                for field in view_model.selected_work_order_detail.fields
            ],
            "state": view_model.selected_work_order_detail.state,
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
        "formSourceWorkRequestOptions": serialize_selector_options(
            view_model.form_source_work_request_options
        ),
        "formWorkOrderTypeOptions": serialize_selector_options(
            view_model.form_work_order_type_options
        ),
        "formPriorityOptions": serialize_selector_options(
            view_model.form_priority_options
        ),
        "formStatusOptions": serialize_selector_options(view_model.form_status_options),
        "formEmployeeOptions": serialize_selector_options(
            view_model.form_employee_options
        ),
        "formVendorOptions": serialize_selector_options(view_model.form_vendor_options),
        "emptyState": view_model.empty_state,
    }


__all__ = [
    "serialize_assets_workspace_state",
    "serialize_dashboard_workspace_state",
    "serialize_planner_workspace_state",
    "serialize_reliability_workspace_state",
    "serialize_selector_options",
    "serialize_work_order_workspace_state",
    "serialize_work_request_workspace_state",
    "serialize_workspace_view_model",
]
