from __future__ import annotations


def set_site_filter(ctrl, site_id: str) -> None:
    normalized = (site_id or "").strip() or "all"
    if normalized == ctrl._selected_site_filter:
        return
    ctrl._set_selected_site_filter(normalized)
    ctrl.refresh()


def set_storeroom_filter(ctrl, storeroom_id: str) -> None:
    normalized = (storeroom_id or "").strip() or "all"
    if normalized == ctrl._selected_storeroom_filter:
        return
    ctrl._set_selected_storeroom_filter(normalized)
    ctrl.refresh()


def set_supplier_filter(ctrl, supplier_id: str) -> None:
    normalized = (supplier_id or "").strip() or "all"
    if normalized == ctrl._selected_supplier_filter:
        return
    ctrl._set_selected_supplier_filter(normalized)
    ctrl.refresh()


def set_limit_filter(ctrl, limit_value: str) -> None:
    normalized = (limit_value or "").strip() or "200"
    if normalized == ctrl._selected_limit_filter:
        return
    ctrl._set_selected_limit_filter(normalized)
    ctrl.refresh()


def clear_filters(ctrl) -> None:
    ctrl._set_selected_site_filter("all")
    ctrl._set_selected_storeroom_filter("all")
    ctrl._set_selected_supplier_filter("all")
    ctrl.refresh()
