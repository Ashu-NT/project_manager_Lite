from __future__ import annotations


def set_requisition_bulk_selection(ctrl, row_id: str, selected: bool) -> None:
    ids = list(ctrl._selected_requisition_ids)
    if selected and row_id not in ids:
        ids.append(row_id)
    elif not selected and row_id in ids:
        ids.remove(row_id)
    ctrl._set_selected_requisition_ids(ids)


def clear_requisition_bulk_selection(ctrl) -> None:
    ctrl._set_selected_requisition_ids([])


def select_visible_requisitions(ctrl) -> None:
    all_ids = [
        str(r.get("id", ""))
        for r in ctrl._requisitions.get("items", [])
        if r.get("id")
    ]
    ctrl._set_selected_requisition_ids(all_ids)


def set_purchase_order_bulk_selection(ctrl, row_id: str, selected: bool) -> None:
    ids = list(ctrl._selected_purchase_order_ids)
    if selected and row_id not in ids:
        ids.append(row_id)
    elif not selected and row_id in ids:
        ids.remove(row_id)
    ctrl._set_selected_purchase_order_ids(ids)


def clear_purchase_order_bulk_selection(ctrl) -> None:
    ctrl._set_selected_purchase_order_ids([])


def select_visible_purchase_orders(ctrl) -> None:
    all_ids = [
        str(r.get("id", ""))
        for r in ctrl._purchase_orders.get("items", [])
        if r.get("id")
    ]
    ctrl._set_selected_purchase_order_ids(all_ids)
