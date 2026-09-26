from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    safe_error_message,
    serialize_resource_record_view_models,
)


def export_resources(controller, columns: list, file_path: str) -> dict[str, object]:
    from src.ui_qml.modules.project_management.utils.table_exporter import (
        export_to_file,
    )

    controller._set_error_message("")
    try:
        records = controller._resources_workspace_presenter.list_export_records(
            search_text=controller._search_text,
            active_filter=controller._selected_active_filter,
            category_filter=controller._selected_category_filter,
            sort_key=controller._resource_sort_key,
            sort_direction="desc" if controller._resource_sort_direction else "asc",
        )
        rows = serialize_resource_record_view_models(records)
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


__all__ = ["export_resources"]
