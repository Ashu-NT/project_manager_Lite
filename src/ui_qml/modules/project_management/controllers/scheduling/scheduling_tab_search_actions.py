from __future__ import annotations


def set_diagnostics_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._diagnostics_search_text:
        return
    controller._diagnostics_search_text = v
    controller.diagnosticsSearchTextChanged.emit()
    controller.filteredDiagnosticsRowsChanged.emit()
    controller.filteredViolationRowsChanged.emit()
    controller._table_models.diagnostics.set_rows(controller.filteredDiagnosticsRows)
    controller._table_models.violations.set_rows(controller.filteredViolationRows)


def set_resources_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._resources_search_text:
        return
    controller._resources_search_text = v
    controller.resourcesSearchTextChanged.emit()
    controller.filteredResourceRowsChanged.emit()
    controller._table_models.resources_loading.set_rows(controller.filteredResourceRows)


def set_baselines_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._baselines_search_text:
        return
    controller._baselines_search_text = v
    controller.baselinesSearchTextChanged.emit()
    controller.filteredBaselineCompareRowsChanged.emit()
    controller.filteredBaselineRegisterRowsChanged.emit()
    controller._table_models.baseline_compare.set_rows(controller.filteredBaselineCompareRows)
    controller._table_models.baseline_register.set_rows(controller.filteredBaselineRegisterRows)


def set_delays_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._delays_search_text:
        return
    controller._delays_search_text = v
    controller.delaysSearchTextChanged.emit()
    controller.filteredDelayedRowsChanged.emit()
    controller._table_models.delayed.set_rows(controller.filteredDelayedRows)


def set_calendars_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._calendars_search_text:
        return
    controller._calendars_search_text = v
    controller.calendarsSearchTextChanged.emit()
    controller.filteredHolidayRowsChanged.emit()
    controller._table_models.holiday.set_rows(controller.filteredHolidayRows)


__all__ = [
    "set_baselines_search_text",
    "set_calendars_search_text",
    "set_delays_search_text",
    "set_diagnostics_search_text",
    "set_resources_search_text",
]
