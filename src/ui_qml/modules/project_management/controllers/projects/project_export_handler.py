from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_project_record_view_models,
)


def export_projects(controller, columns: list, file_path: str) -> dict[str, object]:
    from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file

    controller._set_error_message("")
    try:
        all_ws = controller._projects_workspace_presenter.build_workspace_state(
            search_text=controller._search_text,
            status_filter=controller._selected_status_filter,
            selected_project_id=None,
            page=1,
            page_size=99999,
        )
        rows = serialize_project_record_view_models(all_ws.projects)
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
