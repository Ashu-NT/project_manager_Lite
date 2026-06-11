from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import serialize_workspace_view_model


def do_refresh(controller) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(controller._workspace_presenter.build_view_model())
        )
        ws = controller._tasks_workspace_presenter.build_workspace_state(
            project_id=controller._selected_project_id or None,
            search_text=controller._search_text,
            status_filter=controller._selected_status_filter,
            priority_filter=controller._selected_priority_filter,
            schedule_filter=controller._selected_schedule_filter,
            selected_task_id=controller._selected_task_id or None,
            selected_assignment_id=controller._selected_assignment_id or None,
            selected_time_period_start=controller._selected_time_period_start,
            selected_time_entry_id=controller._selected_time_entry_id or None,
            page=controller._task_page,
            page_size=controller._task_page_size,
        )
        controller._task_list._update(ws)
        controller._set_selected_task_id(ws.selected_task_id)
        controller._set_selected_project_id(ws.selected_project_id)
        controller._set_selected_status_filter(ws.selected_status_filter)
        controller._set_selected_priority_filter(ws.selected_priority_filter)
        controller._set_selected_schedule_filter(ws.selected_schedule_filter)
        controller._set_search_text(ws.search_text)
        controller._set_empty_state(ws.empty_state)
        controller._set_task_total_count(ws.total_count)
        controller._set_task_page(ws.page)
        controller._set_task_page_size(ws.page_size)
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


__all__ = ["do_refresh"]
