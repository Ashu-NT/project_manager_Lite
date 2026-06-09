from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import run_mutation


def set_project_bulk_selection(controller, project_id: str, selected: bool) -> None:
    normalized_id = (project_id or "").strip()
    if not normalized_id:
        return
    current = list(controller._selected_project_ids)
    if selected and normalized_id not in current:
        current.append(normalized_id)
    elif not selected and normalized_id in current:
        current.remove(normalized_id)
    else:
        return
    controller._set_selected_project_ids(current)


def clear_project_bulk_selection(controller) -> None:
    controller._set_selected_project_ids([])


def select_visible_projects(controller) -> None:
    items = controller._projects.get("items") or []
    visible_ids = [
        str(item.get("id", "") or "")
        for item in items
        if item.get("id")
    ]
    controller._set_selected_project_ids(visible_ids)


def bulk_delete_projects(controller, project_ids: list) -> dict[str, object]:
    ids = [str(pid) for pid in (project_ids or []) if pid]
    if not ids:
        return {}
    return run_mutation(
        operation=lambda: _do_bulk_delete(controller, ids),
        success_message=f"{len(ids)} project(s) deleted.",
        on_success=lambda: on_bulk_mutation_success(controller),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def apply_bulk_status(controller, payload: dict[str, object]) -> dict[str, object]:
    status_value = str(payload.get("status", "") or "").strip()
    ids = list(controller._selected_project_ids)
    if not status_value or not ids:
        return {}
    return run_mutation(
        operation=lambda: _do_bulk_set_status(controller, ids, status_value),
        success_message=f"{len(ids)} project(s) updated.",
        on_success=lambda: on_bulk_mutation_success(controller),
        set_is_busy=controller._set_is_busy,
        set_error_message=controller._set_error_message,
        set_feedback_message=controller._set_feedback_message,
    )


def on_bulk_mutation_success(controller) -> None:
    controller._set_selected_project_ids([])
    controller._request_domain_refresh()


def _do_bulk_delete(controller, ids: list[str]) -> None:
    for project_id in ids:
        controller._projects_workspace_presenter.delete_project(project_id)


def _do_bulk_set_status(controller, ids: list[str], status: str) -> None:
    for project_id in ids:
        controller._projects_workspace_presenter.set_project_status(project_id, status)


__all__ = [
    "apply_bulk_status",
    "bulk_delete_projects",
    "clear_project_bulk_selection",
    "on_bulk_mutation_success",
    "select_visible_projects",
    "set_project_bulk_selection",
]
