from __future__ import annotations

from .utils import normalize_project_id, normalize_queue_status


def select_project(controller, project_id: str) -> None:
    normalized = normalize_project_id(project_id)
    if normalized == controller._selected_project_id:
        return
    controller._set_selected_project_id(normalized)
    controller._set_selected_assignment_id("")
    controller._set_selected_period_start("")
    controller._set_selected_entry_id("")
    controller.refresh()


def select_assignment(controller, assignment_id: str) -> None:
    normalized = (assignment_id or "").strip()
    if normalized == controller._selected_assignment_id:
        return
    controller._set_selected_assignment_id(normalized)
    controller._set_selected_period_start("")
    controller._set_selected_entry_id("")
    controller.refresh()


def select_period(controller, period_start: str) -> None:
    normalized = (period_start or "").strip()
    if normalized == controller._selected_period_start:
        return
    controller._set_selected_period_start(normalized)
    controller._set_selected_entry_id("")
    controller.refresh()


def set_queue_status(controller, queue_status: str) -> None:
    normalized = normalize_queue_status(queue_status)
    if normalized == controller._selected_queue_status:
        return
    controller._set_selected_queue_status(normalized)
    controller._set_selected_queue_period_id("")
    controller.refresh()


__all__ = ["select_assignment", "select_period", "select_project", "set_queue_status"]
