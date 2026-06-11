from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_preventive_workspace_state,
    serialize_workspace_view_model,
)

from .preventive_property_updates import (
    set_overview,
    set_plan_form_options,
    set_plan_library_state,
    set_plan_task_form_options,
    set_queue_state,
    set_step_form_options,
    set_template_form_options,
    set_template_library_state,
)
from .preventive_state_sync import sync_internal_state_from_maps


def load_workspace_state(controller) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(
                controller._workspace_presenter.build_view_model()
            )
        )
        state = serialize_preventive_workspace_state(
            controller._preventive_workspace_presenter.build_workspace_state(
                queue_site_filter=controller._queue_site_filter,
                queue_due_state_filter=controller._queue_due_state_filter,
                queue_search_text=controller._queue_search_text,
                selected_queue_plan_id=controller._selected_queue_plan_id or None,
                plan_site_filter=controller._plan_site_filter,
                plan_asset_filter=controller._plan_asset_filter,
                plan_system_filter=controller._plan_system_filter,
                plan_active_filter=controller._plan_active_filter,
                plan_status_filter=controller._plan_status_filter,
                plan_type_filter=controller._plan_type_filter,
                plan_trigger_mode_filter=controller._plan_trigger_mode_filter,
                plan_search_text=controller._plan_search_text,
                selected_plan_id=controller._selected_plan_id or None,
                selected_plan_task_id=controller._selected_plan_task_id or None,
                template_active_filter=controller._template_active_filter,
                template_maintenance_type_filter=controller._template_maintenance_type_filter,
                template_status_filter=controller._template_status_filter,
                template_search_text=controller._template_search_text,
                selected_task_template_id=controller._selected_task_template_id or None,
                selected_task_step_id=controller._selected_task_step_id or None,
                generation_results=controller._latest_generation_results,
            )
        )
        set_overview(controller, state["overview"])
        set_queue_state(controller, state["queueState"])
        set_plan_library_state(controller, state["planLibraryState"])
        set_template_library_state(controller, state["templateLibraryState"])
        set_plan_form_options(controller, state["planFormOptions"])
        set_plan_task_form_options(controller, state["planTaskFormOptions"])
        set_template_form_options(controller, state["templateFormOptions"])
        set_step_form_options(controller, state["stepFormOptions"])
        sync_internal_state_from_maps(controller)
        controller._set_empty_state("")
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)
