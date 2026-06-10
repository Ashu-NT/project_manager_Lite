from __future__ import annotations


def set_search_text(ctrl, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == ctrl._search_text:
        return
    ctrl._set_search_text(normalized)
    ctrl.refresh()


def set_status_filter(ctrl, status: str) -> None:
    normalized = (status or "").strip() or "all"
    if normalized == ctrl._selected_status_filter:
        return
    ctrl._set_selected_status_filter(normalized)
    ctrl.refresh()


def set_item_filter(ctrl, item_id: str) -> None:
    normalized = (item_id or "").strip() or "all"
    if normalized == ctrl._selected_item_filter:
        return
    ctrl._set_selected_item_filter(normalized)
    ctrl.refresh()


def set_storeroom_filter(ctrl, storeroom_id: str) -> None:
    normalized = (storeroom_id or "").strip() or "all"
    if normalized == ctrl._selected_storeroom_filter:
        return
    ctrl._set_selected_storeroom_filter(normalized)
    ctrl.refresh()


def clear_filters(ctrl) -> None:
    ctrl._set_selected_status_filter("all")
    ctrl._set_selected_item_filter("all")
    ctrl._set_selected_storeroom_filter("all")
    ctrl._set_search_text("")
    ctrl.refresh()
