from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_project_record_view_models,
)


def export_projects(controller, columns: list, file_path: str) -> dict[str, object]:
    from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file

    controller._set_error_message("")
    try:
        records = controller._projects_workspace_presenter.list_export_records(
            search_text=controller._search_text,
            status_filter=controller._selected_status_filter,
            sort_key=controller._project_sort_key,
            sort_direction=(
                "desc" if controller._project_sort_direction else "asc"
            ),
        )
        rows = serialize_project_record_view_models(records)
        result = export_to_file(rows, list(columns), (file_path or "").strip())
        if result.get("ok"):
            controller._set_feedback_message(result.get("message", "Export complete."))
        else:
            controller._set_error_message(result.get("error", "Export failed."))
        return result
    except Exception as exc:
        controller._set_error_message(str(exc))
        return {"ok": False, "error": str(exc)}


__all__ = ["export_projects"]
