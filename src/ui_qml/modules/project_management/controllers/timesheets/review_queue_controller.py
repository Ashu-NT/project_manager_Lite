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
    controller._set_queue_page_size(page_size)
    controller._set_queue_page(1)
    controller.refresh()


def _apply_queue_query_value(controller, attribute: str, setter, value) -> None:
    if value == getattr(controller, attribute):
        return
    setter(value)
    controller._set_queue_page(1)
    controller._set_selected_queue_period_id("")
    controller.refresh()


def set_queue_search_text(controller, value: str) -> None:
    _apply_queue_query_value(
        controller, "_queue_search_text", controller._set_queue_search_text,
        (value or "").strip(),
    )


def set_queue_project(controller, value: str) -> None:
    _apply_queue_query_value(
        controller, "_selected_queue_project_id", controller._set_selected_queue_project_id,
        (value or "").strip() or "all",
    )


def set_queue_resource(controller, value: str) -> None:
    _apply_queue_query_value(
        controller, "_selected_queue_resource_id", controller._set_selected_queue_resource_id,
        (value or "").strip() or "all",
    )


def set_queue_period_range(controller, start: str, end: str) -> None:
    normalized_start = (start or "").strip()
    normalized_end = (end or "").strip()
    if (
        normalized_start == controller._queue_period_start_from
        and normalized_end == controller._queue_period_start_to
    ):
        return
    controller._set_queue_period_start_from(normalized_start)
    controller._set_queue_period_start_to(normalized_end)
    controller._set_queue_page(1)
    controller._set_selected_queue_period_id("")
    controller.refresh()


def set_queue_sort(controller, key: str, direction: int) -> None:
    normalized_key = (key or "").strip()
    normalized_direction = 1 if direction == 1 else 0
    if not normalized_key:
        return
    if (
        normalized_key == controller._queue_sort_key
        and normalized_direction == controller._queue_sort_direction
    ):
        return
    controller._set_queue_sort_key(normalized_key)
    controller._set_queue_sort_direction(normalized_direction)
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
    "set_queue_period_range",
    "set_queue_project",
    "set_queue_resource",
    "set_queue_search_text",
    "set_queue_sort",
]
