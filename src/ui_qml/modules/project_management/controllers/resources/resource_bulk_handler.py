from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation


def set_resource_bulk_selection(controller, resource_id: str, selected: bool) -> None:
    normalized_id = (resource_id or "").strip()
    if not normalized_id:
        return
    current = list(controller._selected_resource_ids)
    if selected and normalized_id not in current:
        current.append(normalized_id)
    elif not selected and normalized_id in current:
        current.remove(normalized_id)
    else:
        return
    controller._set_selected_resource_ids(current)


def clear_resource_bulk_selection(controller) -> None:
    controller._set_selected_resource_ids([])


def select_visible_resources(controller) -> None:
    items = controller._resources.get("items") or []
    visible_ids = [
        str(item.get("id", "") or "")
        for item in items
        if item.get("id")
    ]
    controller._set_selected_resource_ids(visible_ids)


def bulk_delete_resources(controller, resource_ids: list) -> dict[str, object]:
    ids = [str(rid) for rid in (resource_ids or []) if rid]
    if not ids:
        return {}
    return run_mutation(
        operation=lambda: _do_bulk_delete(controller, ids),
        success_message=f"{len(ids)} resource(s) deleted.",
        on_success=lambda: on_bulk_mutation_success(controller),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def on_bulk_mutation_success(controller) -> None:
    controller._set_selected_resource_ids([])
    controller._request_domain_refresh()


def _do_bulk_delete(controller, ids: list[str]) -> None:
    for resource_id in ids:
        controller._resources_workspace_presenter.delete_resource(resource_id)


__all__ = [
    "bulk_delete_resources",
    "clear_resource_bulk_selection",
    "on_bulk_mutation_success",
    "select_visible_resources",
    "set_resource_bulk_selection",
]
