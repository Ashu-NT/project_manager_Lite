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
        workspace_state = controller._timesheets_workspace_presenter.build_workspace_state(
            project_id=controller._selected_project_id,
            assignment_id=controller._selected_assignment_id or None,
            period_start=controller._selected_period_start,
            queue_status=controller._selected_queue_status,
            selected_entry_id=controller._selected_entry_id or None,
            selected_queue_period_id=controller._selected_queue_period_id or None,
        )
        controller._set_overview(
            serialize_timesheet_overview_view_model(workspace_state.overview)
        )
        controller._set_project_options(
            serialize_selector_options(workspace_state.project_options)
        )
        controller._set_assignment_options(
            serialize_selector_options(workspace_state.assignment_options)
        )
        controller._set_period_options(
            serialize_selector_options(workspace_state.period_options)
        )
        controller._set_queue_status_options(
            serialize_selector_options(workspace_state.queue_status_options)
        )
        controller._set_selected_project_id(workspace_state.selected_project_id)
        controller._set_selected_assignment_id(workspace_state.selected_assignment_id)
        controller._set_selected_period_start(workspace_state.selected_period_start)
        controller._set_selected_queue_status(workspace_state.selected_queue_status)
        controller._set_selected_entry_id(workspace_state.selected_entry_id)
        controller._set_selected_queue_period_id(workspace_state.selected_queue_period_id)
        controller._set_assignment_summary(
            serialize_timesheet_detail_view_model(workspace_state.assignment_summary)
        )
        controller._set_entries(
            serialize_timesheet_collection_view_model(workspace_state.entries)
        )
        controller._set_selected_entry(
            serialize_timesheet_detail_view_model(workspace_state.selected_entry_detail)
        )
        controller._set_review_queue(
            serialize_timesheet_collection_view_model(workspace_state.review_queue)
        )
        controller._set_queue_total_count(len(controller._review_queue.get("items") or []))
        controller._set_review_detail(
            serialize_timesheet_detail_view_model(workspace_state.review_detail)
        )
        controller._set_empty_state(workspace_state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


__all__ = ["refresh_timesheets_workspace"]
