from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityWorkspaceViewModel,
)

from .selector_serializer import serialize_selector_options


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


__all__ = ["serialize_reliability_workspace_state"]
