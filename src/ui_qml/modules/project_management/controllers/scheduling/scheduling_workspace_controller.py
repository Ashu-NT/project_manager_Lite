from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectSchedulingWorkspacePresenter,
)
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from .activity_log_service import ActivityLogService
from .domain_event_binder import bind_scheduling_domain_events
from .filter_service import filter_rows
from .mutation_handler import SchedulingMutationHandler
from .scheduling_calculation_actions import (
    calculate_working_days,
    export_schedule,
    load_variance_records_for_baseline,
    run_compute_schedule_impact,
)
from .scheduling_property_updates import (
    set_activity_feed,
    set_activity_page,
    set_activity_page_size,
    set_activity_total_count,
    set_baseline_compare_rows,
    set_baseline_options,
    set_baseline_register,
    set_baseline_register_rows,
    set_baseline_variance_rows,
    set_baselines,
    set_calendar,
    set_calendar_options,
    set_calendar_summary_rows,
    set_calculator_result,
    set_constraint_rows,
    set_constraint_violations,
    set_constraints,
    set_critical_path,
    set_delayed_activities,
    set_delayed_activity_rows,
    set_dependencies,
    set_dependency_rows,
    set_dependency_task_options,
    set_dependency_type_options,
    set_diagnostics,
    set_diagnostics_rows,
    set_holiday_rows,
    set_overview,
    set_project_options,
    set_resource_loading,
    set_resource_loading_rows,
    set_schedule,
    set_schedule_rows,
    set_search_text,
    set_selected_activity,
    set_selected_activity_id,
    set_selected_baseline_id,
    set_selected_calendar_id,
    set_selected_project_id,
    set_selected_status_filter,
    set_show_critical_only,
    set_show_delayed_only,
    set_status_options,
    set_timeline,
    set_violation_rows,
)
from .scheduling_selection_actions import (
    activate_activity,
    apply_search_text,
    apply_show_critical_only,
    apply_show_delayed_only,
    apply_status_filter,
    clear_filters,
    select_activity,
    select_baseline,
    select_baseline_a,
    select_baseline_b,
    select_calendar,
    select_project,
    set_active_panel,
    set_include_unchanged,
    set_page,
    set_page_size,
)
from .scheduling_state_loader import load_workspace_state
from .scheduling_tab_search_actions import (
    set_baselines_search_text,
    set_calendars_search_text,
    set_delays_search_text,
    set_diagnostics_search_text,
    set_resources_search_text,
)
from .state import (
    default_baselines,
    default_calendar,
    default_collection,
    default_overview,
    default_schedule_impact,
    default_selected_activity,
)
from .table_models import create_scheduling_table_models

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementSchedulingWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    calendarOptionsChanged = Signal()
    baselineOptionsChanged = Signal()
    dependencyTypeOptionsChanged = Signal()
    dependencyTaskOptionsChanged = Signal()
    statusOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    selectedCalendarIdChanged = Signal()
    selectedBaselineIdChanged = Signal()
    selectedStatusFilterChanged = Signal()
    searchTextChanged = Signal()
    showCriticalOnlyChanged = Signal()
    showDelayedOnlyChanged = Signal()
    activityPageChanged = Signal()
    activityPageSizeChanged = Signal()
    activityTotalCountChanged = Signal()
    calendarChanged = Signal()
    baselinesChanged = Signal()
    scheduleChanged = Signal()
    timelineChanged = Signal()
    criticalPathChanged = Signal()
    diagnosticsChanged = Signal()
    delayedActivitiesChanged = Signal()
    resourceLoadingChanged = Signal()
    baselineRegisterChanged = Signal()
    dependenciesChanged = Signal()
    constraintsChanged = Signal()
    constraintViolationsChanged = Signal()
    activityFeedChanged = Signal()
    scheduleRowsChanged = Signal()
    diagnosticsRowsChanged = Signal()
    delayedActivityRowsChanged = Signal()
    resourceLoadingRowsChanged = Signal()
    baselineCompareRowsChanged = Signal()
    baselineRegisterRowsChanged = Signal()
    dependencyRowsChanged = Signal()
    constraintRowsChanged = Signal()
    violationRowsChanged = Signal()
    calendarSummaryRowsChanged = Signal()
    holidayRowsChanged = Signal()
    diagnosticsSearchTextChanged = Signal()
    resourcesSearchTextChanged = Signal()
    baselinesSearchTextChanged = Signal()
    delaysSearchTextChanged = Signal()
    calendarsSearchTextChanged = Signal()
    filteredDiagnosticsRowsChanged = Signal()
    filteredViolationRowsChanged = Signal()
    filteredResourceRowsChanged = Signal()
    filteredBaselineCompareRowsChanged = Signal()
    filteredBaselineRegisterRowsChanged = Signal()
    filteredDelayedRowsChanged = Signal()
    filteredHolidayRowsChanged = Signal()
    selectedActivityChanged = Signal()
    selectedActivityIdChanged = Signal()
    calculatorResultChanged = Signal()
    baselineVarianceRowsChanged = Signal()
    scheduleImpactChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        scheduling_workspace_presenter: ProjectSchedulingWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.scheduling"
        )
        self._scheduling_workspace_presenter = (
            scheduling_workspace_presenter or ProjectSchedulingWorkspacePresenter()
        )
        self._table_models = create_scheduling_table_models(self)
        self._activity_log_svc = ActivityLogService()
        self._mutations = SchedulingMutationHandler(
            presenter=self._scheduling_workspace_presenter,
            activity_log_service=self._activity_log_svc,
            get_project_id=lambda: self._selected_project_id,
            request_domain_refresh=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )
        self._overview: dict[str, object] = default_overview()
        self._project_options: list[dict[str, str]] = []
        self._calendar_options: list[dict[str, str]] = []
        self._baseline_options: list[dict[str, str]] = []
        self._dependency_type_options: list[dict[str, str]] = []
        self._dependency_task_options: list[dict[str, str]] = []
        self._status_options: list[dict[str, str]] = []
        self._selected_project_id = ""
        self._selected_calendar_id = "default"
        self._selected_baseline_id = ""
        self._selected_status_filter = "all"
        self._search_text = ""
        self._show_critical_only = False
        self._show_delayed_only = False
        self._activity_page = 1
        self._activity_page_size = 25
        self._activity_total_count = 0
        self._selected_activity_id = ""
        self._calendar: dict[str, object] = default_calendar()
        self._baselines: dict[str, object] = default_baselines()
        self._schedule: dict[str, object] = default_collection()
        self._timeline: dict[str, object] = default_collection()
        self._critical_path: dict[str, object] = default_collection()
        self._diagnostics: dict[str, object] = default_collection()
        self._delayed_activities: dict[str, object] = default_collection()
        self._resource_loading: dict[str, object] = default_collection()
        self._baseline_register: dict[str, object] = default_collection()
        self._dependencies: dict[str, object] = default_collection()
        self._constraints: dict[str, object] = default_collection()
        self._constraint_violations: dict[str, object] = default_collection()
        self._activity_feed: dict[str, object] = default_collection()
        self._schedule_rows: list[dict[str, object]] = []
        self._diagnostics_rows: list[dict[str, object]] = []
        self._delayed_activity_rows: list[dict[str, object]] = []
        self._resource_loading_rows: list[dict[str, object]] = []
        self._baseline_compare_rows: list[dict[str, object]] = []
        self._baseline_register_rows: list[dict[str, object]] = []
        self._dependency_rows: list[dict[str, object]] = []
        self._constraint_rows: list[dict[str, object]] = []
        self._violation_rows: list[dict[str, object]] = []
        self._calendar_summary_rows: list[dict[str, object]] = []
        self._holiday_rows: list[dict[str, object]] = []
        self._diagnostics_search_text = ""
        self._resources_search_text = ""
        self._baselines_search_text = ""
        self._delays_search_text = ""
        self._calendars_search_text = ""
        self._selected_activity: dict[str, object] = default_selected_activity()
        self._calculator_result = ""
        self._baseline_variance_rows: list[dict[str, object]] = []
        self._schedule_impact: dict[str, object] = default_schedule_impact()
        self._active_panel_id = "activity_timeline"
        bind_scheduling_domain_events(self)
        self.refresh()

    # ── Overview / option properties ──────────────────────────────────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property("QVariantList", notify=calendarOptionsChanged)
    def calendarOptions(self) -> list[dict[str, str]]:
        return self._calendar_options

    @Property("QVariantList", notify=baselineOptionsChanged)
    def baselineOptions(self) -> list[dict[str, str]]:
        return self._baseline_options

    @Property("QVariantList", notify=dependencyTypeOptionsChanged)
    def dependencyTypeOptions(self) -> list[dict[str, str]]:
        return self._dependency_type_options

    @Property("QVariantList", notify=dependencyTaskOptionsChanged)
    def dependencyTaskOptions(self) -> list[dict[str, str]]:
        return self._dependency_task_options

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    # ── Selection state properties ────────────────────────────────────

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property(str, notify=selectedCalendarIdChanged)
    def selectedCalendarId(self) -> str:
        return self._selected_calendar_id

    @Property(str, notify=selectedBaselineIdChanged)
    def selectedBaselineId(self) -> str:
        return self._selected_baseline_id

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property(bool, notify=showCriticalOnlyChanged)
    def showCriticalOnly(self) -> bool:
        return self._show_critical_only

    @Property(bool, notify=showDelayedOnlyChanged)
    def showDelayedOnly(self) -> bool:
        return self._show_delayed_only

    @Property(int, notify=activityPageChanged)
    def activityPage(self) -> int:
        return self._activity_page

    @Property(int, notify=activityPageSizeChanged)
    def activityPageSize(self) -> int:
        return self._activity_page_size

    @Property(int, notify=activityTotalCountChanged)
    def activityTotalCount(self) -> int:
        return self._activity_total_count

    # ── Panel collection properties ───────────────────────────────────

    @Property("QVariantMap", notify=calendarChanged)
    def calendar(self) -> dict[str, object]:
        return self._calendar

    @Property("QVariantMap", notify=baselinesChanged)
    def baselines(self) -> dict[str, object]:
        return self._baselines

    @Property("QVariantMap", notify=scheduleChanged)
    def schedule(self) -> dict[str, object]:
        return self._schedule

    @Property("QVariantMap", notify=timelineChanged)
    def timeline(self) -> dict[str, object]:
        return self._timeline

    @Property("QVariantMap", notify=criticalPathChanged)
    def criticalPath(self) -> dict[str, object]:
        return self._critical_path

    @Property("QVariantMap", notify=diagnosticsChanged)
    def diagnostics(self) -> dict[str, object]:
        return self._diagnostics

    @Property("QVariantMap", notify=delayedActivitiesChanged)
    def delayedActivities(self) -> dict[str, object]:
        return self._delayed_activities

    @Property("QVariantMap", notify=resourceLoadingChanged)
    def resourceLoading(self) -> dict[str, object]:
        return self._resource_loading

    @Property("QVariantMap", notify=baselineRegisterChanged)
    def baselineRegister(self) -> dict[str, object]:
        return self._baseline_register

    @Property("QVariantMap", notify=dependenciesChanged)
    def dependencies(self) -> dict[str, object]:
        return self._dependencies

    @Property("QVariantMap", notify=constraintsChanged)
    def constraints(self) -> dict[str, object]:
        return self._constraints

    @Property("QVariantMap", notify=constraintViolationsChanged)
    def constraintViolations(self) -> dict[str, object]:
        return self._constraint_violations

    @Property("QVariantMap", notify=activityFeedChanged)
    def activityFeed(self) -> dict[str, object]:
        return self._activity_feed

    # ── Raw row list properties ───────────────────────────────────────

    @Property("QVariantList", notify=scheduleRowsChanged)
    def scheduleRows(self) -> list[dict[str, object]]:
        return self._schedule_rows

    @Property("QVariantList", notify=diagnosticsRowsChanged)
    def diagnosticsRows(self) -> list[dict[str, object]]:
        return self._diagnostics_rows

    @Property("QVariantList", notify=delayedActivityRowsChanged)
    def delayedActivityRows(self) -> list[dict[str, object]]:
        return self._delayed_activity_rows

    @Property("QVariantList", notify=resourceLoadingRowsChanged)
    def resourceLoadingRows(self) -> list[dict[str, object]]:
        return self._resource_loading_rows

    @Property("QVariantList", notify=baselineCompareRowsChanged)
    def baselineCompareRows(self) -> list[dict[str, object]]:
        return self._baseline_compare_rows

    @Property("QVariantList", notify=baselineRegisterRowsChanged)
    def baselineRegisterRows(self) -> list[dict[str, object]]:
        return self._baseline_register_rows

    @Property("QVariantList", notify=dependencyRowsChanged)
    def dependencyRows(self) -> list[dict[str, object]]:
        return self._dependency_rows

    @Property("QVariantList", notify=constraintRowsChanged)
    def constraintRows(self) -> list[dict[str, object]]:
        return self._constraint_rows

    @Property("QVariantList", notify=violationRowsChanged)
    def violationRows(self) -> list[dict[str, object]]:
        return self._violation_rows

    @Property("QVariantList", notify=calendarSummaryRowsChanged)
    def calendarSummaryRows(self) -> list[dict[str, object]]:
        return self._calendar_summary_rows

    @Property("QVariantList", notify=holidayRowsChanged)
    def holidayRows(self) -> list[dict[str, object]]:
        return self._holiday_rows

    # ── Tab-local search text properties ─────────────────────────────

    @Property(str, notify=diagnosticsSearchTextChanged)
    def diagnosticsSearchText(self) -> str:
        return self._diagnostics_search_text

    @Property(str, notify=resourcesSearchTextChanged)
    def resourcesSearchText(self) -> str:
        return self._resources_search_text

    @Property(str, notify=baselinesSearchTextChanged)
    def baselinesSearchText(self) -> str:
        return self._baselines_search_text

    @Property(str, notify=delaysSearchTextChanged)
    def delaysSearchText(self) -> str:
        return self._delays_search_text

    @Property(str, notify=calendarsSearchTextChanged)
    def calendarsSearchText(self) -> str:
        return self._calendars_search_text

    # ── Pre-filtered row properties ───────────────────────────────────

    @Property("QVariantList", notify=filteredDiagnosticsRowsChanged)
    def filteredDiagnosticsRows(self) -> list[dict[str, object]]:
        return filter_rows(self._diagnostics_rows, self._diagnostics_search_text,
                           ["message", "severity", "metric", "status", "details"])

    @Property("QVariantList", notify=filteredViolationRowsChanged)
    def filteredViolationRows(self) -> list[dict[str, object]]:
        return filter_rows(self._violation_rows, self._diagnostics_search_text,
                           ["activity", "constraintType", "required", "computed", "severity"])

    @Property("QVariantList", notify=filteredResourceRowsChanged)
    def filteredResourceRows(self) -> list[dict[str, object]]:
        return filter_rows(self._resource_loading_rows, self._resources_search_text,
                           ["resource", "allocation", "capacity", "utilization", "tasks", "status"])

    @Property("QVariantList", notify=filteredBaselineCompareRowsChanged)
    def filteredBaselineCompareRows(self) -> list[dict[str, object]]:
        return filter_rows(self._baseline_compare_rows, self._baselines_search_text,
                           ["activity", "change", "shift", "dates", "cost"])

    @Property("QVariantList", notify=filteredBaselineRegisterRowsChanged)
    def filteredBaselineRegisterRows(self) -> list[dict[str, object]]:
        return filter_rows(self._baseline_register_rows, self._baselines_search_text,
                           ["baseline", "created", "approvedBy", "status"])

    @Property("QVariantList", notify=filteredDelayedRowsChanged)
    def filteredDelayedRows(self) -> list[dict[str, object]]:
        return filter_rows(self._delayed_activity_rows, self._delays_search_text,
                           ["activity", "finish", "deadline", "delay", "progress", "status"])

    @Property("QVariantList", notify=filteredHolidayRowsChanged)
    def filteredHolidayRows(self) -> list[dict[str, object]]:
        return filter_rows(self._holiday_rows, self._calendars_search_text,
                           ["date", "exception", "calendar", "details"])

    # ── Table model properties ────────────────────────────────────────

    @Property(QObject, constant=True)
    def scheduleTableModel(self) -> DynamicTableModel:
        return self._table_models.schedule

    @Property(QObject, constant=True)
    def scheduleImpactTasksTableModel(self) -> DynamicTableModel:
        return self._table_models.schedule_impact_tasks

    @Property(QObject, constant=True)
    def dependencyTableModel(self) -> DynamicTableModel:
        return self._table_models.dependency

    @Property(QObject, constant=True)
    def constraintTableModel(self) -> DynamicTableModel:
        return self._table_models.constraint

    @Property(QObject, constant=True)
    def calendarSummaryTableModel(self) -> DynamicTableModel:
        return self._table_models.calendar_summary

    @Property(QObject, constant=True)
    def baselineVarianceTableModel(self) -> DynamicTableModel:
        return self._table_models.baseline_variance

    @Property(QObject, constant=True)
    def diagnosticsTableModel(self) -> DynamicTableModel:
        return self._table_models.diagnostics

    @Property(QObject, constant=True)
    def violationsTableModel(self) -> DynamicTableModel:
        return self._table_models.violations

    @Property(QObject, constant=True)
    def resourcesLoadingTableModel(self) -> DynamicTableModel:
        return self._table_models.resources_loading

    @Property(QObject, constant=True)
    def baselineCompareTableModel(self) -> DynamicTableModel:
        return self._table_models.baseline_compare

    @Property(QObject, constant=True)
    def baselineRegisterTableModel(self) -> DynamicTableModel:
        return self._table_models.baseline_register

    @Property(QObject, constant=True)
    def delayedTableModel(self) -> DynamicTableModel:
        return self._table_models.delayed

    @Property(QObject, constant=True)
    def holidayTableModel(self) -> DynamicTableModel:
        return self._table_models.holiday

    # ── Activity / calculator / impact properties ─────────────────────

    @Property("QVariantMap", notify=selectedActivityChanged)
    def selectedActivity(self) -> dict[str, object]:
        return self._selected_activity

    @Property(str, notify=selectedActivityIdChanged)
    def selectedActivityId(self) -> str:
        return self._selected_activity_id

    @Property(str, notify=calculatorResultChanged)
    def calculatorResult(self) -> str:
        return self._calculator_result

    @Property("QVariantList", notify=baselineVarianceRowsChanged)
    def baselineVarianceRows(self) -> list[dict[str, object]]:
        return self._baseline_variance_rows

    @Property("QVariantMap", notify=scheduleImpactChanged)
    def scheduleImpact(self) -> dict[str, object]:
        return self._schedule_impact

    # ── Refresh ───────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        load_workspace_state(self)

    # ── Panel / filter / selection slots ─────────────────────────────

    @Slot(str)
    def setActivePanel(self, panel_id: str) -> None:
        set_active_panel(self, panel_id)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        select_project(self, project_id)

    @Slot(str)
    def selectCalendar(self, calendar_id: str) -> None:
        select_calendar(self, calendar_id)

    @Slot(str)
    def selectBaseline(self, baseline_id: str) -> None:
        select_baseline(self, baseline_id)

    @Slot(str)
    def selectBaselineA(self, baseline_id: str) -> None:
        select_baseline_a(self, baseline_id)

    @Slot(str)
    def selectBaselineB(self, baseline_id: str) -> None:
        select_baseline_b(self, baseline_id)

    @Slot(bool)
    def setIncludeUnchanged(self, include_unchanged: bool) -> None:
        set_include_unchanged(self, include_unchanged)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        apply_search_text(self, search_text)

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        apply_status_filter(self, status_filter)

    @Slot(bool)
    def setShowCriticalOnly(self, enabled: bool) -> None:
        apply_show_critical_only(self, enabled)

    @Slot(bool)
    def setShowDelayedOnly(self, enabled: bool) -> None:
        apply_show_delayed_only(self, enabled)

    @Slot()
    def clearFilters(self) -> None:
        clear_filters(self)

    @Slot(str)
    def selectActivity(self, activity_id: str) -> None:
        select_activity(self, activity_id)

    @Slot(str)
    def activateActivity(self, activity_id: str) -> None:
        activate_activity(self, activity_id)

    @Slot(int)
    def setActivityPage(self, page: int) -> None:
        set_page(self, page)

    @Slot(int)
    def setActivityPageSize(self, page_size: int) -> None:
        set_page_size(self, page_size)

    # ── Tab-local search text slots ───────────────────────────────────

    @Slot(str)
    def setDiagnosticsSearchText(self, text: str) -> None:
        set_diagnostics_search_text(self, text)

    @Slot(str)
    def setResourcesSearchText(self, text: str) -> None:
        set_resources_search_text(self, text)

    @Slot(str)
    def setBaselinesSearchText(self, text: str) -> None:
        set_baselines_search_text(self, text)

    @Slot(str)
    def setDelaysSearchText(self, text: str) -> None:
        set_delays_search_text(self, text)

    @Slot(str)
    def setCalendarsSearchText(self, text: str) -> None:
        set_calendars_search_text(self, text)

    # ── Mutation slots ────────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def createBaseline(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.create_baseline(payload)

    @Slot(str, result="QVariantMap")
    def deleteBaseline(self, baseline_id: str) -> dict[str, object]:
        return self._mutations.delete_baseline(baseline_id)

    @Slot(str, result="QVariantMap")
    def submitBaseline(self, baseline_id: str) -> dict[str, object]:
        return self._mutations.submit_baseline(baseline_id)

    @Slot(str, result="QVariantMap")
    def approveBaseline(self, baseline_id: str) -> dict[str, object]:
        return self._mutations.approve_baseline(baseline_id)

    @Slot(str, result="QVariantMap")
    def rejectBaseline(self, baseline_id: str) -> dict[str, object]:
        return self._mutations.reject_baseline(baseline_id)

    @Slot(result="QVariantMap")
    def recalculateSchedule(self) -> dict[str, object]:
        return self._mutations.recalculate_schedule()

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.create_dependency(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return self._mutations.update_dependency(payload)

    @Slot(str, result="QVariantMap")
    def deleteDependency(self, dependency_id: str) -> dict[str, object]:
        return self._mutations.delete_dependency(dependency_id)

    # ── Calculation slots ─────────────────────────────────────────────

    @Slot("QVariantMap", result="QVariantMap")
    def calculateWorkingDays(self, payload: dict[str, object]) -> dict[str, object]:
        return calculate_working_days(self, payload)

    @Slot(result="QVariantMap")
    def exportSchedule(self) -> dict[str, object]:
        return export_schedule(self)

    @Slot(str)
    def loadVarianceRecordsForBaseline(self, baseline_id: str) -> None:
        load_variance_records_for_baseline(self, baseline_id)

    @Slot("QVariantMap", result="QVariantMap")
    def computeScheduleImpact(self, payload: dict) -> dict[str, object]:
        return run_compute_schedule_impact(self, payload)

    # ── State setters ─────────────────────────────────────────────────

    def _set_overview(self, v): set_overview(self, v)
    def _set_project_options(self, v): set_project_options(self, v)
    def _set_calendar_options(self, v): set_calendar_options(self, v)
    def _set_baseline_options(self, v): set_baseline_options(self, v)
    def _set_dependency_type_options(self, v): set_dependency_type_options(self, v)
    def _set_dependency_task_options(self, v): set_dependency_task_options(self, v)
    def _set_status_options(self, v): set_status_options(self, v)
    def _set_selected_project_id(self, v): set_selected_project_id(self, v)
    def _set_selected_calendar_id(self, v): set_selected_calendar_id(self, v)
    def _set_selected_baseline_id(self, v): set_selected_baseline_id(self, v)
    def _set_selected_status_filter(self, v): set_selected_status_filter(self, v)
    def _set_search_text(self, v): set_search_text(self, v)
    def _set_show_critical_only(self, v): set_show_critical_only(self, v)
    def _set_show_delayed_only(self, v): set_show_delayed_only(self, v)
    def _set_activity_page(self, v): set_activity_page(self, v)
    def _set_activity_page_size(self, v): set_activity_page_size(self, v)
    def _set_activity_total_count(self, v): set_activity_total_count(self, v)
    def _set_selected_activity_id(self, v): set_selected_activity_id(self, v)
    def _set_calendar(self, v): set_calendar(self, v)
    def _set_baselines(self, v): set_baselines(self, v)
    def _set_schedule(self, v): set_schedule(self, v)
    def _set_timeline(self, v): set_timeline(self, v)
    def _set_critical_path(self, v): set_critical_path(self, v)
    def _set_diagnostics(self, v): set_diagnostics(self, v)
    def _set_delayed_activities(self, v): set_delayed_activities(self, v)
    def _set_resource_loading(self, v): set_resource_loading(self, v)
    def _set_baseline_register(self, v): set_baseline_register(self, v)
    def _set_dependencies(self, v): set_dependencies(self, v)
    def _set_constraints(self, v): set_constraints(self, v)
    def _set_constraint_violations(self, v): set_constraint_violations(self, v)
    def _set_activity_feed(self, v): set_activity_feed(self, v)
    def _set_schedule_rows(self, rows): set_schedule_rows(self, rows)
    def _set_diagnostics_rows(self, rows): set_diagnostics_rows(self, rows)
    def _set_delayed_activity_rows(self, rows): set_delayed_activity_rows(self, rows)
    def _set_resource_loading_rows(self, rows): set_resource_loading_rows(self, rows)
    def _set_baseline_compare_rows(self, rows): set_baseline_compare_rows(self, rows)
    def _set_baseline_register_rows(self, rows): set_baseline_register_rows(self, rows)
    def _set_dependency_rows(self, rows): set_dependency_rows(self, rows)
    def _set_constraint_rows(self, rows): set_constraint_rows(self, rows)
    def _set_violation_rows(self, rows): set_violation_rows(self, rows)
    def _set_calendar_summary_rows(self, rows): set_calendar_summary_rows(self, rows)
    def _set_holiday_rows(self, rows): set_holiday_rows(self, rows)
    def _set_selected_activity(self, v): set_selected_activity(self, v)
    def _set_calculator_result(self, v): set_calculator_result(self, v)
    def _set_baseline_variance_rows(self, rows): set_baseline_variance_rows(self, rows)


__all__ = ["ProjectManagementSchedulingWorkspaceController"]
