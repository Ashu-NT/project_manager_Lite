from __future__ import annotations


def set_overview(controller, v: dict[str, object]) -> None:
    if v == controller._overview:
        return
    controller._overview = v
    controller.overviewChanged.emit()


def set_project_options(controller, v: list[dict[str, str]]) -> None:
    if v == controller._project_options:
        return
    controller._project_options = v
    controller.projectOptionsChanged.emit()


def set_assignment_options(controller, v: list[dict[str, str]]) -> None:
    if v == controller._assignment_options:
        return
    controller._assignment_options = v
    controller.assignmentOptionsChanged.emit()


def set_period_options(controller, v: list[dict[str, str]]) -> None:
    if v == controller._period_options:
        return
    controller._period_options = v
    controller.periodOptionsChanged.emit()


def set_queue_status_options(controller, v: list[dict[str, str]]) -> None:
    if v == controller._queue_status_options:
        return
    controller._queue_status_options = v
    controller.queueStatusOptionsChanged.emit()


def set_selected_project_id(controller, v: str) -> None:
    if v == controller._selected_project_id:
        return
    controller._selected_project_id = v
    controller.selectedProjectIdChanged.emit()


def set_selected_assignment_id(controller, v: str) -> None:
    if v == controller._selected_assignment_id:
        return
    controller._selected_assignment_id = v
    controller.selectedAssignmentIdChanged.emit()


def set_selected_period_start(controller, v: str) -> None:
    if v == controller._selected_period_start:
        return
    controller._selected_period_start = v
    controller.selectedPeriodStartChanged.emit()


def set_selected_queue_status(controller, v: str) -> None:
    if v == controller._selected_queue_status:
        return
    controller._selected_queue_status = v
    controller.selectedQueueStatusChanged.emit()


def set_selected_entry_id(controller, v: str) -> None:
    if v == controller._selected_entry_id:
        return
    controller._selected_entry_id = v
    controller.selectedEntryIdChanged.emit()


def set_selected_queue_period_id(controller, v: str) -> None:
    if v == controller._selected_queue_period_id:
        return
    controller._selected_queue_period_id = v
    controller.selectedQueuePeriodIdChanged.emit()


def set_assignment_summary(controller, v: dict[str, object]) -> None:
    if v == controller._assignment_summary:
        return
    controller._assignment_summary = v
    controller.assignmentSummaryChanged.emit()


def set_entries(controller, v: dict[str, object]) -> None:
    if v == controller._entries:
        return
    controller._entries = v
    controller._table_models.entries.set_rows(v.get("items", []))
    controller.entriesChanged.emit()


def set_selected_entry(controller, v: dict[str, object]) -> None:
    if v == controller._selected_entry:
        return
    controller._selected_entry = v
    controller.selectedEntryChanged.emit()


def set_review_queue(controller, v: dict[str, object]) -> None:
    if v == controller._review_queue:
        return
    controller._review_queue = v
    controller._table_models.review_queue.set_rows(v.get("items", []))
    controller.reviewQueueChanged.emit()


def set_review_detail(controller, v: dict[str, object]) -> None:
    if v == controller._review_detail:
        return
    controller._review_detail = v
    controller.reviewDetailChanged.emit()


def set_queue_page(controller, v: int) -> None:
    if v == controller._queue_page:
        return
    controller._queue_page = v
    controller.queuePageChanged.emit()


def set_queue_total_count(controller, v: int) -> None:
    if v == controller._queue_total_count:
        return
    controller._queue_total_count = v
    controller.queueTotalCountChanged.emit()


def set_selected_queue_period_ids(controller, ids: list[str]) -> None:
    if ids == controller._selected_queue_period_ids:
        return
    controller._selected_queue_period_ids = ids
    controller.selectedQueuePeriodIdsChanged.emit()
    controller.selectedQueuePeriodCountChanged.emit()


__all__ = [
    "set_assignment_options",
    "set_assignment_summary",
    "set_entries",
    "set_overview",
    "set_period_options",
    "set_project_options",
    "set_queue_page",
    "set_queue_status_options",
    "set_queue_total_count",
    "set_review_detail",
    "set_review_queue",
    "set_selected_assignment_id",
    "set_selected_entry",
    "set_selected_entry_id",
    "set_selected_period_start",
    "set_selected_project_id",
    "set_selected_queue_period_id",
    "set_selected_queue_period_ids",
    "set_selected_queue_status",
]
