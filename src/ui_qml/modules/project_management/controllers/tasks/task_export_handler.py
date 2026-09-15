from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    safe_error_message,
    serialize_task_record_view_models,
)


def export_tasks(controller, columns: list, file_path: str) -> dict[str, object]:
    from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file

    controller._set_error_message("")
    try:
        records = controller._tasks_workspace_presenter.list_export_records(
            project_id=controller._selected_project_id or None,
            search_text=controller._search_text,
            status_filter=controller._selected_status_filter,
            priority_filter=controller._selected_priority_filter,
            schedule_filter=controller._selected_schedule_filter,
            sort_key=controller._task_sort_key,
            sort_direction="desc" if controller._task_sort_direction else "asc",
        )
        rows = serialize_task_record_view_models(records)
        result = export_to_file(rows, list(columns), (file_path or "").strip())
        if result.get("ok"):
            controller._set_feedback_message(result.get("message", "Export complete."))
        else:
            controller._set_error_message(result.get("error", "Export failed."))
        return result
    except Exception as exc:
        message = safe_error_message(exc, safe_message="The export could not be completed.")
        controller._set_error_message(message)
        return {"ok": False, "error": message}


__all__ = ["export_tasks"]
