from __future__ import annotations

from .plan_detail_builder import build_plan_detail
from .plan_mapper import plan_record
from .plan_task_detail_builder import build_plan_task_detail
from .plan_task_mapper import plan_task_record


def build_plan_empty_state(
    *,
    plan_rows_all,
    plan_search_text: str,
    site_filter: str,
    asset_filter: str,
    system_filter: str,
    active_filter: str,
    status_filter: str,
    plan_type_filter: str,
    trigger_mode_filter: str,
) -> str:
    if plan_rows_all:
        return ""
    if any(
        value != "all"
        for value in (
            site_filter,
            asset_filter,
            system_filter,
            active_filter,
            status_filter,
            plan_type_filter,
            trigger_mode_filter,
        )
    ) or plan_search_text:
        return "No preventive plans match the current filters."
    return "No preventive plans are available yet. Create a plan to start the library."


def build_plan_library_state(
    *,
    site_filter_options,
    asset_filter_options,
    system_filter_options,
    active_filter_options,
    plan_status_options,
    plan_type_options,
    trigger_mode_options,
    normalized_plan_site_filter: str,
    normalized_plan_asset_filter: str,
    normalized_plan_system_filter: str,
    normalized_plan_active_filter: str,
    normalized_plan_status_filter: str,
    normalized_plan_type_filter: str,
    normalized_plan_trigger_mode_filter: str,
    normalized_plan_search: str,
    plan_rows_all,
    resolved_plan_id: str,
    selected_plan,
    plan_task_rows,
    resolved_plan_task_id: str,
    selected_plan_task,
) -> dict[str, object]:
    return {
        "siteOptions": site_filter_options,
        "assetOptions": asset_filter_options,
        "systemOptions": system_filter_options,
        "activeOptions": active_filter_options,
        "statusOptions": plan_status_options,
        "planTypeOptions": plan_type_options,
        "triggerModeOptions": trigger_mode_options,
        "selectedSiteFilter": normalized_plan_site_filter,
        "selectedAssetFilter": normalized_plan_asset_filter,
        "selectedSystemFilter": normalized_plan_system_filter,
        "selectedActiveFilter": normalized_plan_active_filter,
        "selectedStatusFilter": normalized_plan_status_filter,
        "selectedPlanTypeFilter": normalized_plan_type_filter,
        "selectedTriggerModeFilter": normalized_plan_trigger_mode_filter,
        "searchText": normalized_plan_search,
        "plans": {
            "title": "Plan Library",
            "subtitle": "Maintain preventive plans, anchor context, trigger rules, and lifecycle status on the typed desktop API.",
            "emptyState": build_plan_empty_state(
                plan_rows_all=plan_rows_all,
                plan_search_text=normalized_plan_search,
                site_filter=normalized_plan_site_filter,
                asset_filter=normalized_plan_asset_filter,
                system_filter=normalized_plan_system_filter,
                active_filter=normalized_plan_active_filter,
                status_filter=normalized_plan_status_filter,
                plan_type_filter=normalized_plan_type_filter,
                trigger_mode_filter=normalized_plan_trigger_mode_filter,
            ),
            "items": [plan_record(row) for row in plan_rows_all],
        },
        "selectedPlanId": resolved_plan_id,
        "selectedPlan": build_plan_detail(
            selected_plan,
            empty_state="Select a preventive plan to inspect trigger settings, lead generation, and plan-task composition.",
        ),
        "planTasks": {
            "title": "Plan Tasks",
            "subtitle": "Plan-task overrides, sequence order, and trigger-scope adjustments for the selected plan.",
            "emptyState": (
                "Select a preventive plan to review its plan-task overrides."
                if not resolved_plan_id
                else "No plan tasks are configured for the selected preventive plan yet."
            ),
            "items": [plan_task_record(row) for row in plan_task_rows],
        },
        "selectedPlanTaskId": resolved_plan_task_id,
        "selectedPlanTask": build_plan_task_detail(selected_plan_task),
    }
