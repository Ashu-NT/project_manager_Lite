from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_timesheet_detail_view_model,
)


def set_queue_page(controller, page: int) -> None:
    p = max(1, page)
    if p == controller._queue_page:
        return
    controller._set_queue_page(p)
    controller.refresh()


def set_queue_page_size(controller, page_size: int) -> None:
    if page_size <= 0 or page_size == controller._queue_page_size:
        return
    controller._queue_page_size = page_size
    controller.queuePageSizeChanged.emit()
    controller._set_queue_page(1)
    controller.refresh()


def set_queue_bulk_selection(controller, period_id: str, selected: bool) -> None:
    ids = list(controller._selected_queue_period_ids)
    if selected:
        if period_id not in ids:
            ids.append(period_id)
    else:
        ids = [i for i in ids if i != period_id]
    controller._set_selected_queue_period_ids(ids)


def select_visible_queue_periods(controller) -> None:
    ids = [
        str(item.get("id", ""))
        for item in (controller._review_queue.get("items") or [])
        if item.get("id")
    ]
    controller._set_selected_queue_period_ids(ids)


def clear_queue_bulk_selection(controller) -> None:
    controller._set_selected_queue_period_ids([])


def load_queue_period_detail(controller, period_id: str) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        review_detail = controller._timesheets_workspace_presenter.build_review_period_detail(
            period_id
        )
        controller._set_review_detail(serialize_timesheet_detail_view_model(review_detail))
    except Exception as exc:
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


__all__ = [
    "clear_queue_bulk_selection",
    "load_queue_period_detail",
    "select_visible_queue_periods",
    "set_queue_bulk_selection",
    "set_queue_page",
    "set_queue_page_size",
]
