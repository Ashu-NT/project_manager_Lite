from __future__ import annotations

import logging
from time import perf_counter

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_scheduling_collection_view_model,
    serialize_scheduling_detail_view_model,
    serialize_scheduling_overview_view_model,
    serialize_selector_options,
    serialize_workspace_view_model,
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
from .panel_hydrator import hydrate_visible_panel_models, serialize_workspace_panels
from .row_builders import build_baseline_variance_rows
from .schedule_impact_controller import compute_schedule_impact, format_impact_tasks
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

logger = logging.getLogger(__name__)


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
        started = perf_counter()
        logger.info(
            "PM scheduling refresh begin project=%s calendar=%s baseline=%s panel=%s "
            "status_filter=%s search=%s page=%s page_size=%s critical_only=%s delayed_only=%s",
            self._selected_project_id, self._selected_calendar_id, self._selected_baseline_id,
            self._active_panel_id, self._selected_status_filter, self._search_text,
            self._activity_page, self._activity_page_size,
            self._show_critical_only, self._show_delayed_only,
        )
        self._set_is_loading(True)
        success = False
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(self._workspace_presenter.build_view_model())
            )
            ws = self._scheduling_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id or None,
                selected_calendar_id=self._selected_calendar_id or None,
                selected_baseline_id=self._selected_baseline_id or None,
                selected_baseline_a_id=self._baselines.get("selectedBaselineAId") or None,
                selected_baseline_b_id=self._baselines.get("selectedBaselineBId") or None,
                selected_status_filter=self._selected_status_filter,
                search_text=self._search_text,
                show_critical_only=self._show_critical_only,
                show_delayed_only=self._show_delayed_only,
                page=self._activity_page,
                page_size=self._activity_page_size,
                selected_activity_id=self._selected_activity_id or None,
                include_unchanged=bool(self._baselines.get("includeUnchanged", False)),
                activity_log=tuple(self._activity_log_svc.log),
            )
            self._set_overview(serialize_scheduling_overview_view_model(ws.overview))
            self._set_project_options(serialize_selector_options(ws.project_options))
            self._set_calendar_options(serialize_selector_options(ws.calendar_options))
            self._set_baseline_options(serialize_selector_options(ws.baseline_options))
            self._set_dependency_type_options(
                serialize_selector_options(ws.dependency_type_options)
            )
            self._set_dependency_task_options(
                serialize_selector_options(ws.dependency_task_options)
            )
            self._set_status_options(serialize_selector_options(ws.status_options))
            self._set_selected_project_id(ws.selected_project_id)
            self._set_selected_calendar_id(ws.selected_calendar_id)
            self._set_selected_baseline_id(ws.selected_baseline_id)
            self._set_selected_status_filter(ws.selected_status_filter)
            self._set_search_text(ws.search_text)
            self._set_show_critical_only(ws.show_critical_only)
            self._set_show_delayed_only(ws.show_delayed_only)
            self._set_activity_page(ws.page)
            self._set_activity_page_size(ws.page_size)
            self._set_activity_total_count(ws.total_count)
            self._set_selected_activity_id(ws.selected_activity_id)
            panels = serialize_workspace_panels(ws)
            hydrate_visible_panel_models(self, panels)
            self._set_selected_activity(
                serialize_scheduling_detail_view_model(ws.selected_activity_detail)
            )
            self._set_empty_state(
                ws.schedule.empty_state or ws.selected_activity_detail.empty_state
            )
            success = True
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("PM scheduling refresh failed")
            self._set_error_message(str(exc))
        finally:
            duration_ms = (perf_counter() - started) * 1000
            log_method = logger.warning if duration_ms > 500 else logger.info
            log_method(
                "PM scheduling refresh complete success=%s duration_ms=%.1f project=%s panel=%s "
                "schedule_rows=%s total_count=%s diagnostics_rows=%s delayed_rows=%s resource_rows=%s",
                success, duration_ms, self._selected_project_id, self._active_panel_id,
                len(self._schedule.get("items", []) or []),
                self._activity_total_count,
                len(self._diagnostics.get("items", []) or []),
                len(self._delayed_activities.get("items", []) or []),
                len(self._resource_loading.get("items", []) or []),
            )
            self._set_is_loading(False)

    # ── Panel / filter / selection slots ─────────────────────────────

    @Slot(str)
    def setActivePanel(self, panel_id: str) -> None:
        normalized = (panel_id or "").strip() or "activity_timeline"
        if normalized == self._active_panel_id:
            return
        self._active_panel_id = normalized
        self.refresh()

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized = (project_id or "").strip()
        if normalized == self._selected_project_id:
            return
        self._set_selected_project_id(normalized)
        self._set_selected_baseline_id("")
        self._set_selected_activity_id("")
        self._set_baselines({
            **self._baselines,
            "selectedBaselineAId": "",
            "selectedBaselineBId": "",
            "includeUnchanged": False,
        })
        self._activity_page = 1
        self.activityPageChanged.emit()
        self._activity_log_svc.reset()
        self._set_baseline_variance_rows([])
        self.refresh()

    @Slot(str)
    def selectCalendar(self, calendar_id: str) -> None:
        normalized = (calendar_id or "").strip() or "default"
        if normalized == self._selected_calendar_id:
            return
        self._set_selected_calendar_id(normalized)
        self.refresh()

    @Slot(str)
    def selectBaseline(self, baseline_id: str) -> None:
        normalized = (baseline_id or "").strip()
        if normalized == self._selected_baseline_id:
            return
        self._set_selected_baseline_id(normalized)
        self._set_baselines({**self._baselines, "selectedBaselineAId": normalized})
        self.refresh()

    @Slot(str)
    def selectBaselineA(self, baseline_id: str) -> None:
        normalized = (baseline_id or "").strip()
        if normalized == str(self._baselines.get("selectedBaselineAId") or ""):
            return
        self._set_baselines({**self._baselines, "selectedBaselineAId": normalized})
        self.refresh()

    @Slot(str)
    def selectBaselineB(self, baseline_id: str) -> None:
        normalized = (baseline_id or "").strip()
        if normalized == str(self._baselines.get("selectedBaselineBId") or ""):
            return
        self._set_baselines({**self._baselines, "selectedBaselineBId": normalized})
        self.refresh()

    @Slot(bool)
    def setIncludeUnchanged(self, include_unchanged: bool) -> None:
        if bool(self._baselines.get("includeUnchanged", False)) == include_unchanged:
            return
        self._set_baselines({**self._baselines, "includeUnchanged": include_unchanged})
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._search_text:
            return
        self._set_search_text(normalized)
        self._set_activity_page(1)
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        normalized = (status_filter or "").strip() or "all"
        if normalized == self._selected_status_filter:
            return
        self._set_selected_status_filter(normalized)
        self._set_activity_page(1)
        self.refresh()

    @Slot(bool)
    def setShowCriticalOnly(self, enabled: bool) -> None:
        if enabled == self._show_critical_only:
            return
        self._set_show_critical_only(enabled)
        self._set_activity_page(1)
        self.refresh()

    @Slot(bool)
    def setShowDelayedOnly(self, enabled: bool) -> None:
        if enabled == self._show_delayed_only:
            return
        self._set_show_delayed_only(enabled)
        self._set_activity_page(1)
        self.refresh()

    @Slot()
    def clearFilters(self) -> None:
        if (
            not self._search_text
            and self._selected_status_filter == "all"
            and not self._show_critical_only
            and not self._show_delayed_only
        ):
            return
        self._set_search_text("")
        self._set_selected_status_filter("all")
        self._set_show_critical_only(False)
        self._set_show_delayed_only(False)
        self._set_activity_page(1)
        self.refresh()

    @Slot(str)
    def selectActivity(self, activity_id: str) -> None:
        normalized = (activity_id or "").strip()
        if normalized == self._selected_activity_id:
            return
        self._set_selected_activity_id(normalized)

    @Slot(str)
    def activateActivity(self, activity_id: str) -> None:
        self.selectActivity(activity_id)
        QTimer.singleShot(0, self.refresh)

    @Slot(int)
    def setActivityPage(self, page: int) -> None:
        resolved = max(1, int(page or 1))
        if resolved == self._activity_page:
            return
        self._set_activity_page(resolved)
        self.refresh()

    @Slot(int)
    def setActivityPageSize(self, page_size: int) -> None:
        resolved = max(10, int(page_size or 25))
        if resolved == self._activity_page_size:
            return
        self._set_activity_page_size(resolved)
        self._set_activity_page(1)
        self.refresh()

    # ── Tab-local search text slots ───────────────────────────────────

    @Slot(str)
    def setDiagnosticsSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._diagnostics_search_text:
            return
        self._diagnostics_search_text = v
        self.diagnosticsSearchTextChanged.emit()
        self.filteredDiagnosticsRowsChanged.emit()
        self.filteredViolationRowsChanged.emit()
        self._table_models.diagnostics.set_rows(self.filteredDiagnosticsRows)
        self._table_models.violations.set_rows(self.filteredViolationRows)

    @Slot(str)
    def setResourcesSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._resources_search_text:
            return
        self._resources_search_text = v
        self.resourcesSearchTextChanged.emit()
        self.filteredResourceRowsChanged.emit()
        self._table_models.resources_loading.set_rows(self.filteredResourceRows)

    @Slot(str)
    def setBaselinesSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._baselines_search_text:
            return
        self._baselines_search_text = v
        self.baselinesSearchTextChanged.emit()
        self.filteredBaselineCompareRowsChanged.emit()
        self.filteredBaselineRegisterRowsChanged.emit()
        self._table_models.baseline_compare.set_rows(self.filteredBaselineCompareRows)
        self._table_models.baseline_register.set_rows(self.filteredBaselineRegisterRows)

    @Slot(str)
    def setDelaysSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._delays_search_text:
            return
        self._delays_search_text = v
        self.delaysSearchTextChanged.emit()
        self.filteredDelayedRowsChanged.emit()
        self._table_models.delayed.set_rows(self.filteredDelayedRows)

    @Slot(str)
    def setCalendarsSearchText(self, text: str) -> None:
        v = (text or "").strip()
        if v == self._calendars_search_text:
            return
        self._calendars_search_text = v
        self.calendarsSearchTextChanged.emit()
        self.filteredHolidayRowsChanged.emit()
        self._table_models.holiday.set_rows(self.filteredHolidayRows)

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

    @Slot("QVariantMap", result="QVariantMap")
    def calculateWorkingDays(self, payload: dict[str, object]) -> dict[str, object]:
        self._set_error_message("")
        try:
            result = self._scheduling_workspace_presenter.calculate_working_days(dict(payload))
        except Exception as exc:
            self._set_calculator_result("")
            self._set_feedback_message("")
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}
        self._set_calculator_result(result)
        self._set_feedback_message("")
        self._activity_log_svc.record(
            title="Working-day calculation completed",
            status_label="Info",
            subtitle=result,
            meta_text=str(payload.get("startDate", "") or ""),
        )
        self.refresh()
        return {"ok": True, "message": result}

    @Slot(result="QVariantMap")
    def exportSchedule(self) -> dict[str, object]:
        try:
            message = self._scheduling_workspace_presenter.export_schedule(
                self._selected_project_id
            )
        except Exception as exc:
            self._set_error_message(str(exc))
            self._set_feedback_message("")
            return {"ok": False, "message": str(exc)}
        self._set_error_message("")
        self._set_feedback_message(message)
        self._activity_log_svc.record(
            title="Schedule export requested",
            status_label="Info",
            subtitle="Export adapter pending",
            meta_text=self._selected_project_id or "Current project",
        )
        self.refresh()
        return {"ok": True, "message": message}

    @Slot(str)
    def loadVarianceRecordsForBaseline(self, baseline_id: str) -> None:
        normalized_id = (baseline_id or "").strip()
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            collection = self._scheduling_workspace_presenter.build_baseline_variance_collection(
                normalized_id
            )
            serialized = serialize_scheduling_collection_view_model(collection)
            self._set_baseline_variance_rows(build_baseline_variance_rows(serialized))
        except Exception as exc:
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot("QVariantMap", result="QVariantMap")
    def computeScheduleImpact(self, payload: dict) -> dict[str, object]:
        impact, ok, error = compute_schedule_impact(
            self._scheduling_workspace_presenter,
            payload,
            self._selected_activity_id,
            self._selected_project_id,
        )
        if not ok:
            return {"ok": False, "message": error}
        if impact != self._schedule_impact:
            self._schedule_impact = impact
            self._table_models.schedule_impact_tasks.set_rows(
                format_impact_tasks(impact.get("affectedTasks", []))
                if isinstance(impact, dict) else []
            )
            self.scheduleImpactChanged.emit()
        return {"ok": True, "message": "Impact analysis complete."}

    # ── State setters ─────────────────────────────────────────────────

    def _set_overview(self, v: dict[str, object]) -> None:
        if v == self._overview:
            return
        self._overview = v
        self.overviewChanged.emit()

    def _set_project_options(self, v: list[dict[str, str]]) -> None:
        if v == self._project_options:
            return
        self._project_options = v
        self.projectOptionsChanged.emit()

    def _set_calendar_options(self, v: list[dict[str, str]]) -> None:
        if v == self._calendar_options:
            return
        self._calendar_options = v
        self.calendarOptionsChanged.emit()

    def _set_baseline_options(self, v: list[dict[str, str]]) -> None:
        if v == self._baseline_options:
            return
        self._baseline_options = v
        self.baselineOptionsChanged.emit()

    def _set_dependency_type_options(self, v: list[dict[str, str]]) -> None:
        if v == self._dependency_type_options:
            return
        self._dependency_type_options = v
        self.dependencyTypeOptionsChanged.emit()

    def _set_dependency_task_options(self, v: list[dict[str, str]]) -> None:
        if v == self._dependency_task_options:
            return
        self._dependency_task_options = v
        self.dependencyTaskOptionsChanged.emit()

    def _set_status_options(self, v: list[dict[str, str]]) -> None:
        if v == self._status_options:
            return
        self._status_options = v
        self.statusOptionsChanged.emit()

    def _set_selected_project_id(self, v: str) -> None:
        if v == self._selected_project_id:
            return
        self._selected_project_id = v
        self.selectedProjectIdChanged.emit()

    def _set_selected_calendar_id(self, v: str) -> None:
        if v == self._selected_calendar_id:
            return
        self._selected_calendar_id = v
        self.selectedCalendarIdChanged.emit()

    def _set_selected_baseline_id(self, v: str) -> None:
        if v == self._selected_baseline_id:
            return
        self._selected_baseline_id = v
        self.selectedBaselineIdChanged.emit()

    def _set_selected_status_filter(self, v: str) -> None:
        if v == self._selected_status_filter:
            return
        self._selected_status_filter = v
        self.selectedStatusFilterChanged.emit()

    def _set_search_text(self, v: str) -> None:
        if v == self._search_text:
            return
        self._search_text = v
        self.searchTextChanged.emit()

    def _set_show_critical_only(self, v: bool) -> None:
        if v == self._show_critical_only:
            return
        self._show_critical_only = v
        self.showCriticalOnlyChanged.emit()

    def _set_show_delayed_only(self, v: bool) -> None:
        if v == self._show_delayed_only:
            return
        self._show_delayed_only = v
        self.showDelayedOnlyChanged.emit()

    def _set_activity_page(self, v: int) -> None:
        if v == self._activity_page:
            return
        self._activity_page = v
        self.activityPageChanged.emit()

    def _set_activity_page_size(self, v: int) -> None:
        if v == self._activity_page_size:
            return
        self._activity_page_size = v
        self.activityPageSizeChanged.emit()

    def _set_activity_total_count(self, v: int) -> None:
        if v == self._activity_total_count:
            return
        self._activity_total_count = v
        self.activityTotalCountChanged.emit()

    def _set_selected_activity_id(self, v: str) -> None:
        if v == self._selected_activity_id:
            return
        self._selected_activity_id = v
        self.selectedActivityIdChanged.emit()

    def _set_calendar(self, v: dict[str, object]) -> None:
        if v == self._calendar:
            return
        self._calendar = v
        self.calendarChanged.emit()

    def _set_baselines(self, v: dict[str, object]) -> None:
        if v == self._baselines:
            return
        self._baselines = v
        self.baselinesChanged.emit()

    def _set_schedule(self, v: dict[str, object]) -> None:
        if v == self._schedule:
            return
        self._schedule = v
        self.scheduleChanged.emit()

    def _set_timeline(self, v: dict[str, object]) -> None:
        if v == self._timeline:
            return
        self._timeline = v
        self.timelineChanged.emit()

    def _set_critical_path(self, v: dict[str, object]) -> None:
        if v == self._critical_path:
            return
        self._critical_path = v
        self.criticalPathChanged.emit()

    def _set_diagnostics(self, v: dict[str, object]) -> None:
        if v == self._diagnostics:
            return
        self._diagnostics = v
        self.diagnosticsChanged.emit()

    def _set_delayed_activities(self, v: dict[str, object]) -> None:
        if v == self._delayed_activities:
            return
        self._delayed_activities = v
        self.delayedActivitiesChanged.emit()

    def _set_resource_loading(self, v: dict[str, object]) -> None:
        if v == self._resource_loading:
            return
        self._resource_loading = v
        self.resourceLoadingChanged.emit()

    def _set_baseline_register(self, v: dict[str, object]) -> None:
        if v == self._baseline_register:
            return
        self._baseline_register = v
        self.baselineRegisterChanged.emit()

    def _set_dependencies(self, v: dict[str, object]) -> None:
        if v == self._dependencies:
            return
        self._dependencies = v
        self.dependenciesChanged.emit()

    def _set_constraints(self, v: dict[str, object]) -> None:
        if v == self._constraints:
            return
        self._constraints = v
        self.constraintsChanged.emit()

    def _set_constraint_violations(self, v: dict[str, object]) -> None:
        if v == self._constraint_violations:
            return
        self._constraint_violations = v
        self.constraintViolationsChanged.emit()

    def _set_activity_feed(self, v: dict[str, object]) -> None:
        if v == self._activity_feed:
            return
        self._activity_feed = v
        self.activityFeedChanged.emit()

    def _set_schedule_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._schedule_rows:
            return
        self._schedule_rows = rows
        self._table_models.schedule.set_rows(rows)
        self.scheduleRowsChanged.emit()

    def _set_diagnostics_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._diagnostics_rows:
            return
        self._diagnostics_rows = rows
        self.diagnosticsRowsChanged.emit()
        self.filteredDiagnosticsRowsChanged.emit()
        self._table_models.diagnostics.set_rows(self.filteredDiagnosticsRows)

    def _set_delayed_activity_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._delayed_activity_rows:
            return
        self._delayed_activity_rows = rows
        self.delayedActivityRowsChanged.emit()
        self.filteredDelayedRowsChanged.emit()
        self._table_models.delayed.set_rows(self.filteredDelayedRows)

    def _set_resource_loading_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._resource_loading_rows:
            return
        self._resource_loading_rows = rows
        self.resourceLoadingRowsChanged.emit()
        self.filteredResourceRowsChanged.emit()
        self._table_models.resources_loading.set_rows(self.filteredResourceRows)

    def _set_baseline_compare_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._baseline_compare_rows:
            return
        self._baseline_compare_rows = rows
        self.baselineCompareRowsChanged.emit()
        self.filteredBaselineCompareRowsChanged.emit()
        self._table_models.baseline_compare.set_rows(self.filteredBaselineCompareRows)

    def _set_baseline_register_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._baseline_register_rows:
            return
        self._baseline_register_rows = rows
        self.baselineRegisterRowsChanged.emit()
        self.filteredBaselineRegisterRowsChanged.emit()
        self._table_models.baseline_register.set_rows(self.filteredBaselineRegisterRows)

    def _set_dependency_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._dependency_rows:
            return
        self._dependency_rows = rows
        self._table_models.dependency.set_rows(rows)
        self.dependencyRowsChanged.emit()

    def _set_constraint_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._constraint_rows:
            return
        self._constraint_rows = rows
        self._table_models.constraint.set_rows(rows)
        self.constraintRowsChanged.emit()

    def _set_violation_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._violation_rows:
            return
        self._violation_rows = rows
        self.violationRowsChanged.emit()
        self.filteredViolationRowsChanged.emit()
        self._table_models.violations.set_rows(self.filteredViolationRows)

    def _set_calendar_summary_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._calendar_summary_rows:
            return
        self._calendar_summary_rows = rows
        self._table_models.calendar_summary.set_rows(rows)
        self.calendarSummaryRowsChanged.emit()

    def _set_holiday_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._holiday_rows:
            return
        self._holiday_rows = rows
        self.holidayRowsChanged.emit()
        self.filteredHolidayRowsChanged.emit()
        self._table_models.holiday.set_rows(self.filteredHolidayRows)

    def _set_selected_activity(self, v: dict[str, object]) -> None:
        if v == self._selected_activity:
            return
        self._selected_activity = v
        self.selectedActivityChanged.emit()

    def _set_calculator_result(self, v: str) -> None:
        if v == self._calculator_result:
            return
        self._calculator_result = v
        self.calculatorResultChanged.emit()

    def _set_baseline_variance_rows(self, rows: list[dict[str, object]]) -> None:
        if rows == self._baseline_variance_rows:
            return
        self._baseline_variance_rows = rows
        self._table_models.baseline_variance.set_rows(rows)
        self.baselineVarianceRowsChanged.emit()


__all__ = ["ProjectManagementSchedulingWorkspaceController"]
