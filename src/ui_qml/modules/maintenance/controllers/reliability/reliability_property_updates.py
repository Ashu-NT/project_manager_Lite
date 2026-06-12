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


def set_failure_symptom_options(controller, options: list) -> None:
    if options == controller._failure_symptom_options:
        return
    controller._failure_symptom_options = options
    controller.failureSymptomOptionsChanged.emit()


def set_days_options(controller, options: list) -> None:
    if options == controller._days_options:
        return
    controller._days_options = options
    controller.daysOptionsChanged.emit()


def set_limit_options(controller, options: list) -> None:
    if options == controller._limit_options:
        return
    controller._limit_options = options
    controller.limitOptionsChanged.emit()


def set_threshold_options(controller, options: list) -> None:
    if options == controller._threshold_options:
        return
    controller._threshold_options = options
    controller.thresholdOptionsChanged.emit()


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


def set_selected_failure_code_filter(controller, value: str) -> None:
    value = value or "all"
    if value == controller._selected_failure_code_filter:
        return
    controller._selected_failure_code_filter = value
    controller.selectedFailureCodeFilterChanged.emit()


def set_selected_days_filter(controller, value: str) -> None:
    value = value or "90"
    if value == controller._selected_days_filter:
        return
    controller._selected_days_filter = value
    controller.selectedDaysFilterChanged.emit()


def set_selected_limit_filter(controller, value: str) -> None:
    value = value or "20"
    if value == controller._selected_limit_filter:
        return
    controller._selected_limit_filter = value
    controller.selectedLimitFilterChanged.emit()


def set_selected_threshold_filter(controller, value: str) -> None:
    value = value or "2"
    if value == controller._selected_threshold_filter:
        return
    controller._selected_threshold_filter = value
    controller.selectedThresholdFilterChanged.emit()


def set_suggestion_rows(controller, rows: list) -> None:
    if rows == controller._suggestion_rows:
        return
    controller._suggestion_rows = rows
    controller.suggestionRowsChanged.emit()


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
