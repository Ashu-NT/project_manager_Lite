from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation


def set_entry_bulk_selection(controller, entry_id: str, selected: bool) -> None:
    ids = list(controller._selected_entry_ids)
    if selected:
        if entry_id not in ids:
            ids.append(entry_id)
    else:
        ids = [i for i in ids if i != entry_id]
    controller._set_selected_entry_ids(ids)


def select_visible_entries(controller) -> None:
    ids = [
        str(item.get("id", ""))
        for item in (controller._entries.get("items") or [])
        if item.get("id")
    ]
    controller._set_selected_entry_ids(ids)


def clear_entry_bulk_selection(controller) -> None:
    controller._set_selected_entry_ids([])


def bulk_delete_entries(controller, entry_ids: list) -> dict[str, object]:
    ids = [str(i) for i in (entry_ids or [])]
    if not ids:
        return {"ok": False, "message": "No entries selected."}
    return run_mutation(
        operation=lambda: [
            controller._register_workspace_presenter.delete_entry(i) for i in ids
        ],
        success_message=f"{len(ids)} register entry/entries deleted.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def apply_bulk_entry_status(controller, payload: dict[str, object]) -> dict[str, object]:
    ids = list(controller._selected_entry_ids)
    status = str(payload.get("value") or payload.get("status") or "")
    if not ids or not status:
        return {"ok": False, "message": "No entries or status selected."}
    return run_mutation(
        operation=lambda: [
            controller._register_workspace_presenter.update_entry({"id": i, "status": status})
            for i in ids
        ],
        success_message=f"Status updated for {len(ids)} entry/entries.",
        on_success=controller._request_domain_refresh,
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


__all__ = [
    "apply_bulk_entry_status",
    "bulk_delete_entries",
    "clear_entry_bulk_selection",
    "select_visible_entries",
    "set_entry_bulk_selection",
]
