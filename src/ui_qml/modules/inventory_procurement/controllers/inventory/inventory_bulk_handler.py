from __future__ import annotations


def set_balance_bulk_selection(ctrl, row_id: str, selected: bool) -> None:
    ids = list(ctrl._selected_balance_ids)
    if selected and row_id not in ids:
        ids.append(row_id)
    elif not selected and row_id in ids:
        ids.remove(row_id)
    ctrl._set_selected_balance_ids(ids)


def clear_balance_bulk_selection(ctrl) -> None:
    ctrl._set_selected_balance_ids([])


def select_visible_balances(ctrl) -> None:
    all_ids = [
        str(r.get("id", ""))
        for r in ctrl._balances.get("items", [])
        if r.get("id")
    ]
    ctrl._set_selected_balance_ids(all_ids)
