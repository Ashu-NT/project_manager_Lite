from __future__ import annotations


def _set(controller, attribute: str, value, signal) -> None:
    if value != getattr(controller, attribute):
        setattr(controller, attribute, value)
        signal.emit()


def set_overview(c, v): _set(c, "_overview", v, c.overviewChanged)
def set_project_options(c, v): _set(c, "_project_options", v, c.projectOptionsChanged)
def set_queue_status_options(c, v): _set(c, "_queue_status_options", v, c.queueStatusOptionsChanged)
def set_queue_resource_options(c, v): _set(c, "_queue_resource_options", v, c.queueResourceOptionsChanged)
def set_selected_queue_status(c, v): _set(c, "_selected_queue_status", v, c.selectedQueueStatusChanged)
def set_selected_queue_period_id(c, v): _set(c, "_selected_queue_period_id", v, c.selectedQueuePeriodIdChanged)
def set_review_detail(c, v): _set(c, "_review_detail", v, c.reviewDetailChanged)
def set_queue_page(c, v): _set(c, "_queue_page", v, c.queuePageChanged)
def set_queue_page_size(c, v): _set(c, "_queue_page_size", v, c.queuePageSizeChanged)
def set_queue_total_count(c, v): _set(c, "_queue_total_count", v, c.queueTotalCountChanged)
def set_queue_search_text(c, v): _set(c, "_queue_search_text", v, c.queueSearchTextChanged)
def set_selected_queue_project_id(c, v): _set(c, "_selected_queue_project_id", v, c.selectedQueueProjectIdChanged)
def set_selected_queue_resource_id(c, v): _set(c, "_selected_queue_resource_id", v, c.selectedQueueResourceIdChanged)
def set_queue_period_start_from(c, v): _set(c, "_queue_period_start_from", v, c.queuePeriodStartFromChanged)
def set_queue_period_start_to(c, v): _set(c, "_queue_period_start_to", v, c.queuePeriodStartToChanged)
def set_queue_sort_key(c, v): _set(c, "_queue_sort_key", v, c.queueSortKeyChanged)
def set_queue_sort_direction(c, v): _set(c, "_queue_sort_direction", v, c.queueSortDirectionChanged)


def set_review_queue(controller, value) -> None:
    if value != controller._review_queue:
        controller._review_queue = value
        controller._review_queue_table_model.set_rows(value.get("items", []))
        controller.reviewQueueChanged.emit()
