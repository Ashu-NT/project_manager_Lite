from __future__ import annotations

from .task_utils import index_for_option_value, normalize_task_view_state, option_value_for_index


def select_task_view(controller, view_name: str) -> None:
    controller._set_selected_task_view_name((view_name or "").strip())


def save_current_task_view(controller, view_name: str) -> dict[str, object]:
    normalized = (view_name or "").strip()
    if not normalized:
        controller._set_error_message("Saved view name is required.")
        return {"ok": False, "message": "Saved view name is required."}
    state = {
        "query": controller._search_text,
        "status": index_for_option_value(
            controller._task_list.statusOptions, controller._selected_status_filter
        ),
        "priority": index_for_option_value(
            controller._task_list.priorityOptions, controller._selected_priority_filter
        ),
        "schedule": index_for_option_value(
            controller._task_list.scheduleOptions, controller._selected_schedule_filter
        ),
    }
    controller._saved_view_svc.save_view(normalized, state)
    controller._saved_view_svc.persist()
    refresh_task_view_options(controller)
    controller._set_selected_task_view_name(normalized)
    controller._set_error_message("")
    controller._set_feedback_message(f'Saved task view "{normalized}".')
    return {"ok": True, "message": f'Saved task view "{normalized}".'}


def apply_selected_task_view(controller) -> dict[str, object]:
    view_name = controller._selected_task_view_name
    if not view_name:
        controller.refresh()
        return {"ok": True, "message": "Current filters applied."}
    state = controller._saved_view_svc.resolve_view_state(view_name)
    if state is None:
        controller._set_error_message("Saved task view is no longer available.")
        return {"ok": False, "message": "Saved task view is no longer available."}
    apply_task_view_state(controller, state, selected_view_name=view_name)
    controller._set_error_message("")
    controller._set_feedback_message(f'Applied task view "{view_name}".')
    return {"ok": True, "message": f'Applied task view "{view_name}".'}


def delete_selected_task_view(controller) -> dict[str, object]:
    view_name = controller._selected_task_view_name
    if not view_name:
        controller._set_error_message("Choose a saved task view first.")
        return {"ok": False, "message": "Choose a saved task view first."}
    controller._saved_view_svc.delete_view(view_name)
    controller._saved_view_svc.persist()
    refresh_task_view_options(controller)
    controller._set_selected_task_view_name("")
    controller._set_error_message("")
    controller._set_feedback_message(f'Deleted task view "{view_name}".')
    return {"ok": True, "message": f'Deleted task view "{view_name}".'}


def refresh_task_view_options(controller) -> None:
    options = controller._saved_view_svc.build_options()
    if options == controller._task_view_options:
        return
    controller._task_view_options = options
    controller.taskViewOptionsChanged.emit()
    if controller._selected_task_view_name and not controller._saved_view_svc.has_view(
        controller._selected_task_view_name
    ):
        controller._set_selected_task_view_name("")


def apply_task_view_state(
    controller, state: dict[str, object], *, selected_view_name: str
) -> None:
    normalized = normalize_task_view_state(state)
    controller._set_search_text(str(normalized.get("query", "") or ""))
    controller._set_selected_status_filter(
        option_value_for_index(
            controller._task_list.statusOptions,
            normalized.get("status", 0),
            default_value="all",
        )
    )
    controller._set_selected_priority_filter(
        option_value_for_index(
            controller._task_list.priorityOptions,
            normalized.get("priority", 0),
            default_value="all",
        )
    )
    controller._set_selected_schedule_filter(
        option_value_for_index(
            controller._task_list.scheduleOptions,
            normalized.get("schedule", 0),
            default_value="all",
        )
    )
    controller._set_selected_task_view_name(selected_view_name)
    controller._task_page = 1
    controller.refresh()


__all__ = [
    "apply_selected_task_view",
    "apply_task_view_state",
    "delete_selected_task_view",
    "refresh_task_view_options",
    "save_current_task_view",
    "select_task_view",
]
