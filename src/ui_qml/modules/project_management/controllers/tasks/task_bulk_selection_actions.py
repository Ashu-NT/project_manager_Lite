from __future__ import annotations


def set_task_review_active(controller, active: bool) -> None:
    normalized = bool(active)
    if normalized == controller._task_review_active:
        return
    controller._task_review_active = normalized
    controller._collab_ctrl.sync_review_presence(
        controller._selected_task_id if normalized else ""
    )


def set_task_bulk_selection(controller, task_id: str, selected: bool) -> None:
    controller._task_list.setTaskBulkSelection(task_id, selected)


def select_visible_tasks(controller) -> None:
    controller._task_list.selectVisibleTasks()


def clear_task_bulk_selection(controller) -> None:
    controller._task_list.clearTaskBulkSelection()


__all__ = [
    "clear_task_bulk_selection",
    "select_visible_tasks",
    "set_task_bulk_selection",
    "set_task_review_active",
]
