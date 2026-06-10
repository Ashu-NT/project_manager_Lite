from __future__ import annotations


def set_search_text(ctrl, search_text: str) -> None:
    normalized = (search_text or "").strip()
    if normalized == ctrl._search_text:
        return
    ctrl._set_search_text(normalized)
    ctrl.refresh()


def set_site_filter(ctrl, site_id: str) -> None:
    normalized = (site_id or "").strip() or "all"
    if normalized == ctrl._selected_site_filter:
        return
    ctrl._set_selected_site_filter(normalized)
    ctrl.refresh()


def set_active_filter(ctrl, active_filter: str) -> None:
    normalized = (active_filter or "").strip().lower() or "all"
    if normalized == ctrl._selected_active_filter:
        return
    ctrl._set_selected_active_filter(normalized)
    ctrl.refresh()


def set_storeroom_filter(ctrl, storeroom_id: str) -> None:
    normalized = (storeroom_id or "").strip() or "all"
    if normalized == ctrl._selected_storeroom_filter:
        return
    ctrl._set_selected_storeroom_filter(normalized)
    ctrl.refresh()


def set_item_filter(ctrl, item_id: str) -> None:
    normalized = (item_id or "").strip() or "all"
    if normalized == ctrl._selected_item_filter:
        return
    ctrl._set_selected_item_filter(normalized)
    ctrl.refresh()


def set_transaction_type_filter(ctrl, transaction_type: str) -> None:
    normalized = (transaction_type or "").strip() or "all"
    if normalized == ctrl._selected_transaction_type_filter:
        return
    ctrl._set_selected_transaction_type_filter(normalized)
    ctrl.refresh()


def clear_filters(ctrl) -> None:
    ctrl._set_selected_site_filter("all")
    ctrl._set_selected_active_filter("all")
    ctrl._set_selected_storeroom_filter("all")
    ctrl._set_selected_item_filter("all")
    ctrl._set_selected_transaction_type_filter("all")
    ctrl._set_search_text("")
    ctrl.refresh()
