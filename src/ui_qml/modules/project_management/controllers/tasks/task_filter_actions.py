from __future__ import annotations


def set_search_text(controller, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == controller._search_text:
        return
    controller._set_search_text(normalized)
    controller._set_selected_task_view_name("")
    controller._task_page = 1
    controller.refresh()


def set_status_filter(controller, status_filter: str) -> None:
    normalized = (status_filter or "").strip().lower() or "all"
    if normalized == controller._selected_status_filter.lower():
        return
    controller._set_selected_status_filter(normalized)
    controller._set_selected_task_view_name("")
    controller._task_page = 1
    controller.refresh()


def set_priority_filter(controller, priority_filter: str) -> None:
    normalized = (priority_filter or "").strip().lower() or "all"
    if normalized == controller._selected_priority_filter.lower():
        return
    controller._set_selected_priority_filter(normalized)
    controller._set_selected_task_view_name("")
    controller._task_page = 1
    controller.refresh()


def set_schedule_filter(controller, schedule_filter: str) -> None:
    normalized = (schedule_filter or "").strip().lower() or "all"
    if normalized == controller._selected_schedule_filter.lower():
        return
    controller._set_selected_schedule_filter(normalized)
    controller._set_selected_task_view_name("")
    controller._task_page = 1
    controller.refresh()


def clear_filters(controller) -> None:
    if (
        not controller._search_text
        and controller._selected_status_filter == "all"
        and controller._selected_priority_filter == "all"
        and controller._selected_schedule_filter == "all"
        and not controller._selected_task_view_name
    ):
        return
    controller._set_search_text("")
    controller._set_selected_status_filter("all")
    controller._set_selected_priority_filter("all")
    controller._set_selected_schedule_filter("all")
    controller._set_selected_task_view_name("")
    controller._task_page = 1
    controller.refresh()


__all__ = [
    "clear_filters",
    "set_priority_filter",
    "set_schedule_filter",
    "set_search_text",
    "set_status_filter",
]
