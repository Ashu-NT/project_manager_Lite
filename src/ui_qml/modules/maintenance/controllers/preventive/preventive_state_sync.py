from __future__ import annotations


def sync_internal_state_from_maps(controller) -> None:
    queue_state = controller._queue_state or {}
    plan_state = controller._plan_library_state or {}
    template_state = controller._template_library_state or {}

    controller._queue_site_filter = str(
        queue_state.get("selectedSiteFilter", "all") or "all"
    )
    controller._queue_due_state_filter = str(
        queue_state.get("selectedDueStateFilter", "all") or "all"
    )
    controller._queue_search_text = str(queue_state.get("searchText", "") or "")
    controller._selected_queue_plan_id = str(
        queue_state.get("selectedPlanId", "") or ""
    )

    controller._plan_site_filter = str(
        plan_state.get("selectedSiteFilter", "all") or "all"
    )
    controller._plan_asset_filter = str(
        plan_state.get("selectedAssetFilter", "all") or "all"
    )
    controller._plan_system_filter = str(
        plan_state.get("selectedSystemFilter", "all") or "all"
    )
    controller._plan_active_filter = str(
        plan_state.get("selectedActiveFilter", "all") or "all"
    )
    controller._plan_status_filter = str(
        plan_state.get("selectedStatusFilter", "all") or "all"
    )
    controller._plan_type_filter = str(
        plan_state.get("selectedPlanTypeFilter", "all") or "all"
    )
    controller._plan_trigger_mode_filter = str(
        plan_state.get("selectedTriggerModeFilter", "all") or "all"
    )
    controller._plan_search_text = str(plan_state.get("searchText", "") or "")
    controller._selected_plan_id = str(plan_state.get("selectedPlanId", "") or "")
    controller._selected_plan_task_id = str(
        plan_state.get("selectedPlanTaskId", "") or ""
    )

    controller._template_active_filter = str(
        template_state.get("selectedActiveFilter", "all") or "all"
    )
    controller._template_maintenance_type_filter = str(
        template_state.get("selectedMaintenanceTypeFilter", "all") or "all"
    )
    controller._template_status_filter = str(
        template_state.get("selectedStatusFilter", "all") or "all"
    )
    controller._template_search_text = str(template_state.get("searchText", "") or "")
    controller._selected_task_template_id = str(
        template_state.get("selectedTaskTemplateId", "") or ""
    )
    controller._selected_task_step_id = str(
        template_state.get("selectedTaskStepId", "") or ""
    )
