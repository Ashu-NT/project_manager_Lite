from __future__ import annotations


def preview_import(controller, file_path: str, source_format: str) -> dict[str, object]:
    controller._set_import_busy(True)
    controller._set_import_error("")
    try:
        preview = controller._projects_workspace_presenter.preview_import(
            file_path=file_path,
            source_format=source_format,
        )
        controller._set_import_preview(preview)
        return {"ok": True}
    except Exception as exc:
        controller._set_import_error(str(exc))
        return {"ok": False, "error": str(exc)}
    finally:
        controller._set_import_busy(False)


def execute_import(controller, session_id: str) -> dict[str, object]:
    controller._set_import_busy(True)
    controller._set_import_error("")
    try:
        result = controller._projects_workspace_presenter.execute_import(
            session_id=session_id,
        )
        controller._set_feedback_message(result.get("message", "Import completed."))
        controller._set_import_preview({})
        return result
    except Exception as exc:
        controller._set_import_error(str(exc))
        return {"ok": False, "error": str(exc)}
    finally:
        controller._set_import_busy(False)


def cancel_import(controller) -> None:
    controller._set_import_preview({})
    controller._set_import_error("")


__all__ = ["cancel_import", "execute_import", "preview_import"]
