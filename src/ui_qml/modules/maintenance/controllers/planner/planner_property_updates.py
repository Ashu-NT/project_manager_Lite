from __future__ import annotations


def set_overview(controller, overview: dict) -> None:
    if overview == controller._overview:
        return
    controller._overview = overview
    controller.overviewChanged.emit()


def set_site_options(controller, options: list) -> None:
    if options == controller._site_options:
        return
    controller._site_options = options
    controller.siteOptionsChanged.emit()


def set_asset_options(controller, options: list) -> None:
    if options == controller._asset_options:
        return
    controller._asset_options = options
    controller.assetOptionsChanged.emit()


def set_system_options(controller, options: list) -> None:
    if options == controller._system_options:
        return
    controller._system_options = options
    controller.systemOptionsChanged.emit()


def set_request_queue_options(controller, options: list) -> None:
    if options == controller._request_queue_options:
        return
    controller._request_queue_options = options
    controller.requestQueueOptionsChanged.emit()


def set_work_order_queue_options(controller, options: list) -> None:
    if options == controller._work_order_queue_options:
        return
    controller._work_order_queue_options = options
    controller.workOrderQueueOptionsChanged.emit()


def set_selected_site_filter(controller, value: str) -> None:
    value = value or "all"
    if value == controller._selected_site_filter:
        return
    controller._selected_site_filter = value
    controller.selectedSiteFilterChanged.emit()


def set_selected_asset_filter(controller, value: str) -> None:
    value = value or "all"
    if value == controller._selected_asset_filter:
        return
    controller._selected_asset_filter = value
    controller.selectedAssetFilterChanged.emit()


def set_selected_system_filter(controller, value: str) -> None:
    value = value or "all"
    if value == controller._selected_system_filter:
        return
    controller._selected_system_filter = value
    controller.selectedSystemFilterChanged.emit()


def set_selected_request_queue(controller, value: str) -> None:
    if value == controller._selected_request_queue:
        return
    controller._selected_request_queue = value
    controller.selectedRequestQueueChanged.emit()


def set_selected_work_order_queue(controller, value: str) -> None:
    if value == controller._selected_work_order_queue:
        return
    controller._selected_work_order_queue = value
    controller.selectedWorkOrderQueueChanged.emit()


def set_search_text_prop(controller, value: str) -> None:
    if value == controller._search_text:
        return
    controller._search_text = value
    controller.searchTextChanged.emit()


def set_request_rows(controller, rows: list) -> None:
    if rows == controller._request_rows:
        return
    controller._request_rows = rows
    controller.requestRowsChanged.emit()


def set_work_order_rows(controller, rows: list) -> None:
    if rows == controller._work_order_rows:
        return
    controller._work_order_rows = rows
    controller.workOrderRowsChanged.emit()


def set_material_rows(controller, rows: list) -> None:
    if rows == controller._material_rows:
        return
    controller._material_rows = rows
    controller.materialRowsChanged.emit()


def set_preventive_rows(controller, rows: list) -> None:
    if rows == controller._preventive_rows:
        return
    controller._preventive_rows = rows
    controller.preventiveRowsChanged.emit()


def set_recurring_rows(controller, rows: list) -> None:
    if rows == controller._recurring_rows:
        return
    controller._recurring_rows = rows
    controller.recurringRowsChanged.emit()
