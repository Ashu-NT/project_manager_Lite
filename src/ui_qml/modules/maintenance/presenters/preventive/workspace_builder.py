from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.preventive import (
    MaintenancePreventiveWorkspaceViewModel,
)

from .filtering import matches_search, normalize_filter, to_active_only
from .form_options_builder import (
    build_plan_form_options,
    build_plan_task_form_options,
    build_step_form_options,
    build_template_form_options,
)
from .options import active_filter_options, build_task_template_type_options, option
from .overview_builder import build_overview
from .plan_library_builder import build_plan_library_state
from .queue_builder import build_queue_state
from .selection import resolve_selected_id
from .template_library_builder import build_template_library_state


def build_workspace_state(
    desktop_api,
    *,
    queue_site_filter: str = "all",
    queue_due_state_filter: str = "all",
    queue_search_text: str = "",
    selected_queue_plan_id: str | None = None,
    plan_site_filter: str = "all",
    plan_asset_filter: str = "all",
    plan_system_filter: str = "all",
    plan_active_filter: str = "all",
    plan_status_filter: str = "all",
    plan_type_filter: str = "all",
    plan_trigger_mode_filter: str = "all",
    plan_search_text: str = "",
    selected_plan_id: str | None = None,
    selected_plan_task_id: str | None = None,
    template_active_filter: str = "all",
    template_maintenance_type_filter: str = "all",
    template_status_filter: str = "all",
    template_search_text: str = "",
    selected_task_template_id: str | None = None,
    selected_task_step_id: str | None = None,
    generation_results: list[dict[str, object]] | None = None,
) -> MaintenancePreventiveWorkspaceViewModel:
    site_filter_options = [
        option("all", "All sites"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_sites(active_only=None)
        ),
    ]
    due_state_options = [
        option("all", "All due states"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_due_states()
        ),
    ]
    plan_status_options = [
        option("all", "All statuses"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_plan_statuses()
        ),
    ]
    plan_type_options = [
        option("all", "All plan types"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_plan_types()
        ),
    ]
    trigger_mode_options = [
        option("all", "All trigger modes"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_trigger_modes()
        ),
    ]
    task_template_status_options = [
        option("all", "All template statuses"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_task_template_statuses()
        ),
    ]
    task_template_type_options = build_task_template_type_options(desktop_api)
    active_opts = active_filter_options()

    normalized_queue_site_filter = normalize_filter(queue_site_filter, site_filter_options)
    normalized_queue_due_state_filter = normalize_filter(queue_due_state_filter, due_state_options)
    normalized_plan_site_filter = normalize_filter(plan_site_filter, site_filter_options)

    asset_filter_options = [
        option("all", "All assets"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_asset_options(
                active_only=None,
                site_id=None if normalized_plan_site_filter == "all" else normalized_plan_site_filter,
            )
        ),
    ]
    system_filter_options = [
        option("all", "All systems"),
        *(
            option(opt.value, opt.label)
            for opt in desktop_api.list_system_options(
                active_only=None,
                site_id=None if normalized_plan_site_filter == "all" else normalized_plan_site_filter,
            )
        ),
    ]
    normalized_plan_asset_filter = normalize_filter(plan_asset_filter, asset_filter_options)
    normalized_plan_system_filter = normalize_filter(plan_system_filter, system_filter_options)
    normalized_plan_active_filter = normalize_filter(plan_active_filter, active_opts)
    normalized_plan_status_filter = normalize_filter(plan_status_filter, plan_status_options)
    normalized_plan_type_filter = normalize_filter(plan_type_filter, plan_type_options)
    normalized_plan_trigger_mode_filter = normalize_filter(plan_trigger_mode_filter, trigger_mode_options)
    normalized_template_active_filter = normalize_filter(template_active_filter, active_opts)
    normalized_template_maintenance_type_filter = normalize_filter(
        template_maintenance_type_filter,
        task_template_type_options,
    )
    normalized_template_status_filter = normalize_filter(template_status_filter, task_template_status_options)

    normalized_queue_search = (queue_search_text or "").strip()
    normalized_plan_search = (plan_search_text or "").strip()
    normalized_template_search = (template_search_text or "").strip()

    queue_rows_all = desktop_api.list_due_candidates(
        site_id=None if normalized_queue_site_filter == "all" else normalized_queue_site_filter,
    )
    filtered_queue_rows = tuple(
        row
        for row in queue_rows_all
        if (
            normalized_queue_due_state_filter == "all"
            or row.due_state == normalized_queue_due_state_filter
        )
        and matches_search(
            normalized_queue_search,
            row.plan_code,
            row.plan_label,
            row.anchor_label,
            row.plan_status,
            row.due_state,
            row.due_reason,
            row.trigger_label,
            row.generation_target_label,
        )
    )
    resolved_queue_plan_id = resolve_selected_id(
        selected_queue_plan_id,
        filtered_queue_rows,
        id_attr="plan_id",
    )
    selected_queue_plan = next(
        (row for row in filtered_queue_rows if row.plan_id == resolved_queue_plan_id),
        None,
    )
    selected_queue_plan_detail = (
        desktop_api.get_preventive_plan(resolved_queue_plan_id)
        if resolved_queue_plan_id
        else None
    )
    forecast_rows = (
        desktop_api.preview_plan_schedule(plan_id=resolved_queue_plan_id)
        if resolved_queue_plan_id
        else ()
    )

    plan_rows_all = desktop_api.list_preventive_plans(
        active_only=to_active_only(normalized_plan_active_filter),
        site_id=None if normalized_plan_site_filter == "all" else normalized_plan_site_filter,
        asset_id=None if normalized_plan_asset_filter == "all" else normalized_plan_asset_filter,
        system_id=None if normalized_plan_system_filter == "all" else normalized_plan_system_filter,
        status=None if normalized_plan_status_filter == "all" else normalized_plan_status_filter,
        plan_type=None if normalized_plan_type_filter == "all" else normalized_plan_type_filter,
        trigger_mode=None if normalized_plan_trigger_mode_filter == "all" else normalized_plan_trigger_mode_filter,
        search_text=normalized_plan_search,
    )
    resolved_plan_id = resolve_selected_id(selected_plan_id, plan_rows_all)
    selected_plan = next((row for row in plan_rows_all if row.id == resolved_plan_id), None)
    plan_task_rows = (
        desktop_api.list_plan_tasks(plan_id=resolved_plan_id) if resolved_plan_id else ()
    )
    resolved_plan_task_id = resolve_selected_id(selected_plan_task_id, plan_task_rows)
    selected_plan_task = next(
        (row for row in plan_task_rows if row.id == resolved_plan_task_id),
        None,
    )

    template_rows_all = desktop_api.list_task_templates(
        active_only=to_active_only(normalized_template_active_filter),
        maintenance_type=None if normalized_template_maintenance_type_filter == "all" else normalized_template_maintenance_type_filter,
        template_status=None if normalized_template_status_filter == "all" else normalized_template_status_filter,
        search_text=normalized_template_search,
    )
    resolved_task_template_id = resolve_selected_id(selected_task_template_id, template_rows_all)
    selected_task_template = next(
        (row for row in template_rows_all if row.id == resolved_task_template_id),
        None,
    )
    step_rows = (
        desktop_api.list_task_step_templates(
            task_template_id=resolved_task_template_id,
            active_only=None,
        )
        if resolved_task_template_id
        else ()
    )
    resolved_task_step_id = resolve_selected_id(selected_task_step_id, step_rows)
    selected_task_step = next(
        (row for row in step_rows if row.id == resolved_task_step_id),
        None,
    )

    generation_result_rows = generation_results or []

    return MaintenancePreventiveWorkspaceViewModel(
        overview=build_overview(
            queue_rows=queue_rows_all,
            plan_rows=plan_rows_all,
            task_template_rows=template_rows_all,
        ),
        queue_state=build_queue_state(
            site_filter_options=site_filter_options,
            due_state_options=due_state_options,
            normalized_queue_site_filter=normalized_queue_site_filter,
            normalized_queue_due_state_filter=normalized_queue_due_state_filter,
            normalized_queue_search=normalized_queue_search,
            queue_rows_all=queue_rows_all,
            filtered_queue_rows=filtered_queue_rows,
            resolved_queue_plan_id=resolved_queue_plan_id,
            selected_queue_plan_detail=selected_queue_plan_detail,
            selected_queue_plan=selected_queue_plan,
            forecast_rows=forecast_rows,
            generation_result_rows=generation_result_rows,
        ),
        plan_library_state=build_plan_library_state(
            site_filter_options=site_filter_options,
            asset_filter_options=asset_filter_options,
            system_filter_options=system_filter_options,
            active_filter_options=active_opts,
            plan_status_options=plan_status_options,
            plan_type_options=plan_type_options,
            trigger_mode_options=trigger_mode_options,
            normalized_plan_site_filter=normalized_plan_site_filter,
            normalized_plan_asset_filter=normalized_plan_asset_filter,
            normalized_plan_system_filter=normalized_plan_system_filter,
            normalized_plan_active_filter=normalized_plan_active_filter,
            normalized_plan_status_filter=normalized_plan_status_filter,
            normalized_plan_type_filter=normalized_plan_type_filter,
            normalized_plan_trigger_mode_filter=normalized_plan_trigger_mode_filter,
            normalized_plan_search=normalized_plan_search,
            plan_rows_all=plan_rows_all,
            resolved_plan_id=resolved_plan_id,
            selected_plan=selected_plan,
            plan_task_rows=plan_task_rows,
            resolved_plan_task_id=resolved_plan_task_id,
            selected_plan_task=selected_plan_task,
        ),
        template_library_state=build_template_library_state(
            active_filter_options=active_opts,
            task_template_type_options=task_template_type_options,
            task_template_status_options=task_template_status_options,
            normalized_template_active_filter=normalized_template_active_filter,
            normalized_template_maintenance_type_filter=normalized_template_maintenance_type_filter,
            normalized_template_status_filter=normalized_template_status_filter,
            normalized_template_search=normalized_template_search,
            template_rows_all=template_rows_all,
            resolved_task_template_id=resolved_task_template_id,
            selected_task_template=selected_task_template,
            step_rows=step_rows,
            resolved_task_step_id=resolved_task_step_id,
            selected_task_step=selected_task_step,
        ),
        plan_form_options=build_plan_form_options(desktop_api),
        plan_task_form_options=build_plan_task_form_options(desktop_api),
        template_form_options=build_template_form_options(task_template_type_options, desktop_api),
        step_form_options=build_step_form_options(),
    )
