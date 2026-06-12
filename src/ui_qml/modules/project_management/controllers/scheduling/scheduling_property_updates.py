from __future__ import annotations


def set_overview(controller, v: dict) -> None:
    if v == controller._overview:
        return
    controller._overview = v
    controller.overviewChanged.emit()


def set_project_options(controller, v: list) -> None:
    if v == controller._project_options:
        return
    controller._project_options = v
    controller.projectOptionsChanged.emit()


def set_calendar_options(controller, v: list) -> None:
    if v == controller._calendar_options:
        return
    controller._calendar_options = v
    controller.calendarOptionsChanged.emit()


def set_baseline_options(controller, v: list) -> None:
    if v == controller._baseline_options:
        return
    controller._baseline_options = v
    controller.baselineOptionsChanged.emit()


def set_dependency_type_options(controller, v: list) -> None:
    if v == controller._dependency_type_options:
        return
    controller._dependency_type_options = v
    controller.dependencyTypeOptionsChanged.emit()


def set_dependency_task_options(controller, v: list) -> None:
    if v == controller._dependency_task_options:
        return
    controller._dependency_task_options = v
    controller.dependencyTaskOptionsChanged.emit()


def set_status_options(controller, v: list) -> None:
    if v == controller._status_options:
        return
    controller._status_options = v
    controller.statusOptionsChanged.emit()


def set_selected_project_id(controller, v: str) -> None:
    if v == controller._selected_project_id:
        return
    controller._selected_project_id = v
    controller.selectedProjectIdChanged.emit()


def set_selected_calendar_id(controller, v: str) -> None:
    if v == controller._selected_calendar_id:
        return
    controller._selected_calendar_id = v
    controller.selectedCalendarIdChanged.emit()


def set_selected_baseline_id(controller, v: str) -> None:
    if v == controller._selected_baseline_id:
        return
    controller._selected_baseline_id = v
    controller.selectedBaselineIdChanged.emit()


def set_selected_status_filter(controller, v: str) -> None:
    if v == controller._selected_status_filter:
        return
    controller._selected_status_filter = v
    controller.selectedStatusFilterChanged.emit()


def set_search_text(controller, v: str) -> None:
    if v == controller._search_text:
        return
    controller._search_text = v
    controller.searchTextChanged.emit()


def set_show_critical_only(controller, v: bool) -> None:
    if v == controller._show_critical_only:
        return
    controller._show_critical_only = v
    controller.showCriticalOnlyChanged.emit()


def set_show_delayed_only(controller, v: bool) -> None:
    if v == controller._show_delayed_only:
        return
    controller._show_delayed_only = v
    controller.showDelayedOnlyChanged.emit()


def set_activity_page(controller, v: int) -> None:
    if v == controller._activity_page:
        return
    controller._activity_page = v
    controller.activityPageChanged.emit()


def set_activity_page_size(controller, v: int) -> None:
    if v == controller._activity_page_size:
        return
    controller._activity_page_size = v
    controller.activityPageSizeChanged.emit()


def set_activity_total_count(controller, v: int) -> None:
    if v == controller._activity_total_count:
        return
    controller._activity_total_count = v
    controller.activityTotalCountChanged.emit()


def set_selected_activity_id(controller, v: str) -> None:
    if v == controller._selected_activity_id:
        return
    controller._selected_activity_id = v
    controller.selectedActivityIdChanged.emit()


def set_calendar(controller, v: dict) -> None:
    if v == controller._calendar:
        return
    controller._calendar = v
    controller.calendarChanged.emit()


def set_baselines(controller, v: dict) -> None:
    if v == controller._baselines:
        return
    controller._baselines = v
    controller.baselinesChanged.emit()


def set_schedule(controller, v: dict) -> None:
    if v == controller._schedule:
        return
    controller._schedule = v
    controller.scheduleChanged.emit()


def set_timeline(controller, v: dict) -> None:
    if v == controller._timeline:
        return
    controller._timeline = v
    controller.timelineChanged.emit()


def set_critical_path(controller, v: dict) -> None:
    if v == controller._critical_path:
        return
    controller._critical_path = v
    controller.criticalPathChanged.emit()


def set_diagnostics(controller, v: dict) -> None:
    if v == controller._diagnostics:
        return
    controller._diagnostics = v
    controller.diagnosticsChanged.emit()


def set_delayed_activities(controller, v: dict) -> None:
    if v == controller._delayed_activities:
        return
    controller._delayed_activities = v
    controller.delayedActivitiesChanged.emit()


def set_resource_loading(controller, v: dict) -> None:
    if v == controller._resource_loading:
        return
    controller._resource_loading = v
    controller.resourceLoadingChanged.emit()


def set_baseline_register(controller, v: dict) -> None:
    if v == controller._baseline_register:
        return
    controller._baseline_register = v
    controller.baselineRegisterChanged.emit()


def set_dependencies(controller, v: dict) -> None:
    if v == controller._dependencies:
        return
    controller._dependencies = v
    controller.dependenciesChanged.emit()


def set_constraints(controller, v: dict) -> None:
    if v == controller._constraints:
        return
    controller._constraints = v
    controller.constraintsChanged.emit()


def set_constraint_violations(controller, v: dict) -> None:
    if v == controller._constraint_violations:
        return
    controller._constraint_violations = v
    controller.constraintViolationsChanged.emit()


def set_activity_feed(controller, v: dict) -> None:
    if v == controller._activity_feed:
        return
    controller._activity_feed = v
    controller.activityFeedChanged.emit()


def set_schedule_rows(controller, rows: list) -> None:
    if rows == controller._schedule_rows:
        return
    controller._schedule_rows = rows
    controller._table_models.schedule.set_rows(rows)
    controller.scheduleRowsChanged.emit()


def set_diagnostics_rows(controller, rows: list) -> None:
    if rows == controller._diagnostics_rows:
        return
    controller._diagnostics_rows = rows
    controller.diagnosticsRowsChanged.emit()
    controller.filteredDiagnosticsRowsChanged.emit()
    controller._table_models.diagnostics.set_rows(controller.filteredDiagnosticsRows)


def set_delayed_activity_rows(controller, rows: list) -> None:
    if rows == controller._delayed_activity_rows:
        return
    controller._delayed_activity_rows = rows
    controller.delayedActivityRowsChanged.emit()
    controller.filteredDelayedRowsChanged.emit()
    controller._table_models.delayed.set_rows(controller.filteredDelayedRows)


def set_resource_loading_rows(controller, rows: list) -> None:
    if rows == controller._resource_loading_rows:
        return
    controller._resource_loading_rows = rows
    controller.resourceLoadingRowsChanged.emit()
    controller.filteredResourceRowsChanged.emit()
    controller._table_models.resources_loading.set_rows(controller.filteredResourceRows)


def set_baseline_compare_rows(controller, rows: list) -> None:
    if rows == controller._baseline_compare_rows:
        return
    controller._baseline_compare_rows = rows
    controller.baselineCompareRowsChanged.emit()
    controller.filteredBaselineCompareRowsChanged.emit()
    controller._table_models.baseline_compare.set_rows(controller.filteredBaselineCompareRows)


def set_baseline_register_rows(controller, rows: list) -> None:
    if rows == controller._baseline_register_rows:
        return
    controller._baseline_register_rows = rows
    controller.baselineRegisterRowsChanged.emit()
    controller.filteredBaselineRegisterRowsChanged.emit()
    controller._table_models.baseline_register.set_rows(controller.filteredBaselineRegisterRows)


def set_dependency_rows(controller, rows: list) -> None:
    if rows == controller._dependency_rows:
        return
    controller._dependency_rows = rows
    controller._table_models.dependency.set_rows(rows)
    controller.dependencyRowsChanged.emit()


def set_constraint_rows(controller, rows: list) -> None:
    if rows == controller._constraint_rows:
        return
    controller._constraint_rows = rows
    controller._table_models.constraint.set_rows(rows)
    controller.constraintRowsChanged.emit()


def set_violation_rows(controller, rows: list) -> None:
    if rows == controller._violation_rows:
        return
    controller._violation_rows = rows
    controller.violationRowsChanged.emit()
    controller.filteredViolationRowsChanged.emit()
    controller._table_models.violations.set_rows(controller.filteredViolationRows)


def set_calendar_summary_rows(controller, rows: list) -> None:
    if rows == controller._calendar_summary_rows:
        return
    controller._calendar_summary_rows = rows
    controller._table_models.calendar_summary.set_rows(rows)
    controller.calendarSummaryRowsChanged.emit()


def set_holiday_rows(controller, rows: list) -> None:
    if rows == controller._holiday_rows:
        return
    controller._holiday_rows = rows
    controller.holidayRowsChanged.emit()
    controller.filteredHolidayRowsChanged.emit()
    controller._table_models.holiday.set_rows(controller.filteredHolidayRows)


def set_selected_activity(controller, v: dict) -> None:
    if v == controller._selected_activity:
        return
    controller._selected_activity = v
    controller.selectedActivityChanged.emit()


def set_calculator_result(controller, v: str) -> None:
    if v == controller._calculator_result:
        return
    controller._calculator_result = v
    controller.calculatorResultChanged.emit()


def set_baseline_variance_rows(controller, rows: list) -> None:
    if rows == controller._baseline_variance_rows:
        return
    controller._baseline_variance_rows = rows
    controller._table_models.baseline_variance.set_rows(rows)
    controller.baselineVarianceRowsChanged.emit()


__all__ = [
    "set_activity_feed",
    "set_activity_page",
    "set_activity_page_size",
    "set_activity_total_count",
    "set_baseline_compare_rows",
    "set_baseline_options",
    "set_baseline_register",
    "set_baseline_register_rows",
    "set_baseline_variance_rows",
    "set_baselines",
    "set_calendar",
    "set_calendar_options",
    "set_calendar_summary_rows",
    "set_calculator_result",
    "set_constraint_rows",
    "set_constraint_violations",
    "set_constraints",
    "set_critical_path",
    "set_delayed_activities",
    "set_delayed_activity_rows",
    "set_dependencies",
    "set_dependency_rows",
    "set_dependency_task_options",
    "set_dependency_type_options",
    "set_diagnostics",
    "set_diagnostics_rows",
    "set_holiday_rows",
    "set_overview",
    "set_project_options",
    "set_resource_loading",
    "set_resource_loading_rows",
    "set_schedule",
    "set_schedule_rows",
    "set_search_text",
    "set_selected_activity",
    "set_selected_activity_id",
    "set_selected_baseline_id",
    "set_selected_calendar_id",
    "set_selected_project_id",
    "set_selected_status_filter",
    "set_show_critical_only",
    "set_show_delayed_only",
    "set_status_options",
    "set_timeline",
    "set_violation_rows",
]
