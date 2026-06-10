from __future__ import annotations

from PySide6.QtCore import QTimer


def set_search_text(controller, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == controller._search_text:
        return
    controller._set_search_text(normalized)
    controller._resource_page = 1
    controller.refresh()


def set_active_filter(controller, active_filter: str) -> None:
    normalized = (active_filter or "").strip().lower() or "all"
    if normalized == controller._selected_active_filter:
        return
    controller._set_selected_active_filter(normalized)
    controller._resource_page = 1
    controller.refresh()


def set_category_filter(controller, category_filter: str) -> None:
    normalized = (category_filter or "").strip().upper() or "ALL"
    if normalized == controller._selected_category_filter.upper():
        return
    controller._set_selected_category_filter(category_filter)
    controller._resource_page = 1
    controller.refresh()


def select_resource(controller, resource_id: str) -> None:
    normalized = (resource_id or "").strip()
    if normalized == controller._selected_resource_id:
        return
    controller._set_selected_resource_id(normalized)


def activate_resource(controller, resource_id: str) -> None:
    select_resource(controller, resource_id)
    QTimer.singleShot(0, controller.refresh)
    QTimer.singleShot(0, controller.loadResourceAssignments)


def set_resource_page(controller, page: int) -> None:
    p = max(1, page)
    if p == controller._resource_page:
        return
    controller._set_resource_page(p)
    controller.refresh()


def set_resource_page_size(controller, page_size: int) -> None:
    if page_size <= 0 or page_size == controller._resource_page_size:
        return
    controller._resource_page_size = page_size
    controller.resourcePageSizeChanged.emit()
    controller._set_resource_page(1)
    controller.refresh()


__all__ = [
    "activate_resource",
    "select_resource",
    "set_active_filter",
    "set_category_filter",
    "set_resource_page",
    "set_resource_page_size",
    "set_search_text",
]
