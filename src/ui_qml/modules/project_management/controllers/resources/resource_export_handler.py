from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_resource_record_view_models,
)


def export_resources(controller, columns: list, file_path: str) -> dict[str, object]:
    from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file

    controller._set_error_message("")
    try:
        all_ws = controller._resources_workspace_presenter.build_workspace_state(
            search_text=controller._search_text,
            active_filter=controller._selected_active_filter,
            category_filter=controller._selected_category_filter,
            selected_resource_id=None,
            page=1,
            page_size=99999,
        )
        rows = serialize_resource_record_view_models(all_ws.resources)
        result = export_to_file(rows, list(columns), (file_path or "").strip())
        if result.get("ok"):
            controller._set_feedback_message(result.get("message", "Export complete."))
        else:
            controller._set_error_message(result.get("error", "Export failed."))
        return result
    except Exception as exc:
        controller._set_error_message(str(exc))
        return {"ok": False, "error": str(exc)}


__all__ = ["export_resources"]
