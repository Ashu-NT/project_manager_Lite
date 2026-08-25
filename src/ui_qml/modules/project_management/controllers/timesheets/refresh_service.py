from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_selector_options,
    serialize_timesheet_collection_view_model,
    serialize_timesheet_detail_view_model,
    serialize_timesheet_overview_view_model,
    serialize_workspace_view_model,
)


def refresh_timesheets_workspace(controller) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(controller._workspace_presenter.build_view_model())
        )
        state = controller._timesheets_workspace_presenter.build_workspace_state(
            queue_status=controller._selected_queue_status,
            queue_search_text=controller._queue_search_text,
            queue_project_id=controller._selected_queue_project_id,
            queue_resource_id=controller._selected_queue_resource_id,
            queue_period_start_from=controller._queue_period_start_from,
            queue_period_start_to=controller._queue_period_start_to,
            queue_sort_key=controller._queue_sort_key,
            queue_sort_direction="desc" if controller._queue_sort_direction else "asc",
            selected_queue_period_id=controller._selected_queue_period_id or None,
            queue_page=controller._queue_page,
            queue_page_size=controller._queue_page_size,
        )
        controller._set_overview(serialize_timesheet_overview_view_model(state.overview))
        controller._set_project_options(serialize_selector_options(state.project_options))
        controller._set_queue_status_options(serialize_selector_options(state.queue_status_options))
        controller._set_queue_resource_options(serialize_selector_options(state.queue_resource_options))
        controller._set_selected_queue_status(state.selected_queue_status)
        controller._set_queue_search_text(state.queue_search_text)
        controller._set_selected_queue_project_id(state.selected_queue_project_id)
        controller._set_selected_queue_resource_id(state.selected_queue_resource_id)
        controller._set_queue_period_start_from(state.queue_period_start_from)
        controller._set_queue_period_start_to(state.queue_period_start_to)
        controller._set_queue_sort_key(state.queue_sort_key)
        controller._set_queue_sort_direction(1 if state.queue_sort_direction == "desc" else 0)
        controller._set_selected_queue_period_id(state.selected_queue_period_id)
        controller._set_review_queue(serialize_timesheet_collection_view_model(state.review_queue))
        controller._set_review_detail(serialize_timesheet_detail_view_model(state.review_detail))
        controller._set_queue_total_count(state.queue_total_count)
        controller._set_queue_page(state.queue_page)
        controller._set_queue_page_size(state.queue_page_size)
        controller._set_empty_state(state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive QML boundary
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


__all__ = ["refresh_timesheets_workspace"]
