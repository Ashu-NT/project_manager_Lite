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


def set_location_options(controller, options: list) -> None:
    if options == controller._location_options:
        return
    controller._location_options = options
    controller.locationOptionsChanged.emit()


def set_window_options(controller, options: list) -> None:
    if options == controller._window_options:
        return
    controller._window_options = options
    controller.windowOptionsChanged.emit()


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


def set_selected_location_filter(controller, value: str) -> None:
    value = value or "all"
    if value == controller._selected_location_filter:
        return
    controller._selected_location_filter = value
    controller.selectedLocationFilterChanged.emit()


def set_selected_days_filter(controller, value: str) -> None:
    value = value or "90"
    if value == controller._selected_days_filter:
        return
    controller._selected_days_filter = value
    controller.selectedDaysFilterChanged.emit()


def set_backlog_rows(controller, rows: list) -> None:
    if rows == controller._backlog_rows:
        return
    controller._backlog_rows = rows
    controller.backlogRowsChanged.emit()


def set_root_cause_rows(controller, rows: list) -> None:
    if rows == controller._root_cause_rows:
        return
    controller._root_cause_rows = rows
    controller.rootCauseRowsChanged.emit()


def set_recurring_rows(controller, rows: list) -> None:
    if rows == controller._recurring_rows:
        return
    controller._recurring_rows = rows
    controller.recurringRowsChanged.emit()
