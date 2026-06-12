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


def set_requisition_status_filter(ctrl, status: str) -> None:
    normalized = (status or "").strip() or "all"
    if normalized == ctrl._selected_requisition_status_filter:
        return
    ctrl._set_selected_requisition_status_filter(normalized)
    ctrl.refresh()


def set_purchase_order_status_filter(ctrl, status: str) -> None:
    normalized = (status or "").strip() or "all"
    if normalized == ctrl._selected_purchase_order_status_filter:
        return
    ctrl._set_selected_purchase_order_status_filter(normalized)
    ctrl.refresh()


def clear_filters(ctrl) -> None:
    ctrl._set_selected_site_filter("all")
    ctrl._set_selected_storeroom_filter("all")
    ctrl._set_selected_supplier_filter("all")
    ctrl._set_selected_requisition_status_filter("all")
    ctrl._set_selected_purchase_order_status_filter("all")
    ctrl._set_search_text("")
    ctrl.refresh()
