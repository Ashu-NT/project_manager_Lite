from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import run_mutation


def set_item_bulk_selection(ctrl, row_id: str, selected: bool) -> None:
    ids = list(ctrl._selected_item_ids)
    if selected and row_id not in ids:
        ids.append(row_id)
    elif not selected and row_id in ids:
        ids.remove(row_id)
    ctrl._set_selected_item_ids(ids)


def clear_item_bulk_selection(ctrl) -> None:
    ctrl._set_selected_item_ids([])


def select_visible_items(ctrl) -> None:
    all_ids = [
        str(r.get("id", ""))
        for r in ctrl._items.get("items", [])
        if r.get("id")
    ]
    ctrl._set_selected_item_ids(all_ids)


def set_category_bulk_selection(ctrl, row_id: str, selected: bool) -> None:
    ids = list(ctrl._selected_category_ids)
    if selected and row_id not in ids:
        ids.append(row_id)
    elif not selected and row_id in ids:
        ids.remove(row_id)
    ctrl._set_selected_category_ids(ids)


def clear_category_bulk_selection(ctrl) -> None:
    ctrl._set_selected_category_ids([])


def select_visible_categories(ctrl) -> None:
    all_ids = [
        str(r.get("id", ""))
        for r in ctrl._categories.get("items", [])
        if r.get("id")
    ]
    ctrl._set_selected_category_ids(all_ids)


def apply_bulk_status(ctrl, payload: dict) -> dict[str, object]:
    merged = dict(payload)
    merged.setdefault("itemIds", list(ctrl._selected_item_ids))
    return run_mutation(
        operation=lambda: ctrl._catalog_workspace_presenter.apply_bulk_status(merged),
        success_message="Bulk item status applied.",
        on_success=lambda: (ctrl.clearItemBulkSelection(), ctrl.refresh()),
        set_is_busy=ctrl._set_is_busy,
        set_error_message=ctrl._set_error_message,
        set_feedback_message=ctrl._set_feedback_message,
    )
