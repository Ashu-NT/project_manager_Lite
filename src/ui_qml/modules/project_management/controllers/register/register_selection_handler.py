from __future__ import annotations


def select_project(controller, project_id: str) -> None:
    normalized = (project_id or "").strip() or "all"
    if normalized == controller._selected_project_id:
        return
    controller._set_selected_project_id(normalized)
    controller.refresh()


def set_type_filter(controller, type_filter: str) -> None:
    normalized = (type_filter or "").strip() or "all"
    if normalized == controller._selected_type_filter:
        return
    controller._set_selected_type_filter(normalized)
    controller.refresh()


def set_status_filter(controller, status_filter: str) -> None:
    normalized = (status_filter or "").strip() or "all"
    if normalized == controller._selected_status_filter:
        return
    controller._set_selected_status_filter(normalized)
    controller.refresh()


def set_severity_filter(controller, severity_filter: str) -> None:
    normalized = (severity_filter or "").strip() or "all"
    if normalized == controller._selected_severity_filter:
        return
    controller._set_selected_severity_filter(normalized)
    controller.refresh()


def set_search_text(controller, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == controller._search_text:
        return
    controller._set_search_text(normalized)
    controller.refresh()


def select_entry(controller, entry_id: str) -> None:
    normalized = (entry_id or "").strip()
    if normalized == controller._selected_entry_id:
        return
    controller._set_selected_entry_id(normalized)
    controller.refresh()


def set_entry_page(controller, page: int) -> None:
    p = max(1, page)
    if p == controller._entry_page:
        return
    controller._set_entry_page(p)
    controller.refresh()


def set_entry_page_size(controller, page_size: int) -> None:
    if page_size <= 0 or page_size == controller._entry_page_size:
        return
    controller._entry_page_size = page_size
    controller.entryPageSizeChanged.emit()
    controller._set_entry_page(1)
    controller.refresh()


__all__ = [
    "select_entry",
    "select_project",
    "set_entry_page",
    "set_entry_page_size",
    "set_search_text",
    "set_severity_filter",
    "set_status_filter",
    "set_type_filter",
]
