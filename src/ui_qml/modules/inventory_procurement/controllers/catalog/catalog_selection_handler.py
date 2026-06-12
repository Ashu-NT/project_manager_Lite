from __future__ import annotations


def select_category(ctrl, category_id: str) -> None:
    normalized = (category_id or "").strip()
    if normalized == ctrl._selected_category_id:
        return
    ctrl._set_selected_category_id(normalized)
    ctrl.refresh()


def select_item(ctrl, item_id: str) -> None:
    normalized = (item_id or "").strip()
    if normalized == ctrl._selected_item_id:
        return
    ctrl._set_selected_item_id(normalized)
    ctrl.refresh()


def set_active_view(ctrl, view: str) -> None:
    normalized = view if view in ("items", "categories") else "items"
    if normalized == ctrl._active_view:
        return
    ctrl._active_view = normalized
    ctrl.activeViewChanged.emit()


def set_item_page(ctrl, page: int) -> None:
    ctrl._item_page = max(1, int(page))
    ctrl.itemPageChanged.emit()


def set_item_page_size(ctrl, size: int) -> None:
    ctrl._item_page_size = max(10, min(200, int(size)))
    ctrl._item_page = 1
    ctrl.itemPageSizeChanged.emit()
    ctrl.itemPageChanged.emit()


def set_category_page(ctrl, page: int) -> None:
    ctrl._category_page = max(1, int(page))
    ctrl.categoryPageChanged.emit()


def set_category_page_size(ctrl, size: int) -> None:
    ctrl._category_page_size = max(10, min(200, int(size)))
    ctrl._category_page = 1
    ctrl.categoryPageSizeChanged.emit()
    ctrl.categoryPageChanged.emit()
