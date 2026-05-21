from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_scheduling_baselines_view_model,
    serialize_scheduling_calendar_view_model,
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
    activityFeedChanged = Signal()
    selectedActivityChanged = Signal()
    selectedActivityIdChanged = Signal()
    calculatorResultChanged = Signal()

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
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
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
        self._calendar: dict[str, object] = {
            "summaryText": "",
            "workingDays": [],
            "hoursPerDay": "8",
            "holidays": [],
            "emptyState": "",
        }
        self._baselines: dict[str, object] = {
            "options": [],
            "selectedBaselineAId": "",
            "selectedBaselineBId": "",
            "includeUnchanged": False,
            "summaryText": "",
            "rows": [],
            "emptyState": "",
        }
        self._schedule: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._timeline: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._critical_path: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._diagnostics: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._delayed_activities: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._resource_loading: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._baseline_register: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._dependencies: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._constraints: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._activity_feed: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "items": [],
            "emptyState": "",
        }
        self._selected_activity: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._calculator_result = ""
        self._activity_log: list[dict[str, str]] = []
        self._bind_domain_events()
        self.refresh()

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

    @Property("QVariantMap", notify=activityFeedChanged)
    def activityFeed(self) -> dict[str, object]:
        return self._activity_feed

    @Property("QVariantMap", notify=selectedActivityChanged)
    def selectedActivity(self) -> dict[str, object]:
        return self._selected_activity

    @Property(str, notify=selectedActivityIdChanged)
    def selectedActivityId(self) -> str:
        return self._selected_activity_id

    @Property(str, notify=calculatorResultChanged)
    def calculatorResult(self) -> str:
        return self._calculator_result

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(
                    self._workspace_presenter.build_view_model()
                )
            )
            workspace_state = self._scheduling_workspace_presenter.build_workspace_state(
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
                activity_log=tuple(self._activity_log),
            )
            self._set_overview(
                serialize_scheduling_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_calendar_options(
                serialize_selector_options(workspace_state.calendar_options)
            )
            self._set_baseline_options(
                serialize_selector_options(workspace_state.baseline_options)
            )
            self._set_dependency_type_options(
                serialize_selector_options(workspace_state.dependency_type_options)
            )
            self._set_dependency_task_options(
                serialize_selector_options(workspace_state.dependency_task_options)
            )
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_calendar_id(workspace_state.selected_calendar_id)
            self._set_selected_baseline_id(workspace_state.selected_baseline_id)
            self._set_selected_status_filter(workspace_state.selected_status_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_show_critical_only(workspace_state.show_critical_only)
            self._set_show_delayed_only(workspace_state.show_delayed_only)
            self._set_activity_page(workspace_state.page)
            self._set_activity_page_size(workspace_state.page_size)
            self._set_activity_total_count(workspace_state.total_count)
            self._set_selected_activity_id(workspace_state.selected_activity_id)
            self._set_calendar(
                serialize_scheduling_calendar_view_model(workspace_state.calendar)
            )
            self._set_baselines(
                serialize_scheduling_baselines_view_model(workspace_state.baselines)
            )
            self._set_schedule(
                serialize_scheduling_collection_view_model(workspace_state.schedule)
            )
            self._set_timeline(
                serialize_scheduling_collection_view_model(workspace_state.timeline)
            )
            self._set_critical_path(
                serialize_scheduling_collection_view_model(workspace_state.critical_path)
            )
            self._set_diagnostics(
                serialize_scheduling_collection_view_model(workspace_state.diagnostics)
            )
            self._set_delayed_activities(
                serialize_scheduling_collection_view_model(
                    workspace_state.delayed_activities
                )
            )
            self._set_resource_loading(
                serialize_scheduling_collection_view_model(
                    workspace_state.resource_loading
                )
            )
            self._set_baseline_register(
                serialize_scheduling_collection_view_model(
                    workspace_state.baseline_register
                )
            )
            self._set_dependencies(
                serialize_scheduling_collection_view_model(workspace_state.dependencies)
            )
            self._set_constraints(
                serialize_scheduling_collection_view_model(workspace_state.constraints)
            )
            self._set_activity_feed(
                serialize_scheduling_collection_view_model(workspace_state.activity_feed)
            )
            self._set_selected_activity(
                serialize_scheduling_detail_view_model(
                    workspace_state.selected_activity_detail
                )
            )
            self._set_empty_state(
                workspace_state.schedule.empty_state
                or workspace_state.selected_activity_detail.empty_state
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._set_selected_baseline_id("")
        self._set_selected_activity_id("")
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineAId": "",
                "selectedBaselineBId": "",
                "includeUnchanged": False,
            }
        )
        self._activity_page = 1
        self.activityPageChanged.emit()
        self._activity_log = []
        self.refresh()

    @Slot(str)
    def selectCalendar(self, calendar_id: str) -> None:
        normalized_value = (calendar_id or "").strip() or "default"
        if normalized_value == self._selected_calendar_id:
            return
        self._set_selected_calendar_id(normalized_value)
        self.refresh()

    @Slot(str)
    def selectBaseline(self, baseline_id: str) -> None:
        normalized_value = (baseline_id or "").strip()
        if normalized_value == self._selected_baseline_id:
            return
        self._set_selected_baseline_id(normalized_value)
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineAId": normalized_value,
            }
        )
        self.refresh()

    @Slot(str)
    def selectBaselineA(self, baseline_id: str) -> None:
        normalized_value = (baseline_id or "").strip()
        if normalized_value == str(self._baselines.get("selectedBaselineAId") or ""):
            return
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineAId": normalized_value,
            }
        )
        self.refresh()

    @Slot(str)
    def selectBaselineB(self, baseline_id: str) -> None:
        normalized_value = (baseline_id or "").strip()
        if normalized_value == str(self._baselines.get("selectedBaselineBId") or ""):
            return
        self._set_baselines(
            {
                **self._baselines,
                "selectedBaselineBId": normalized_value,
            }
        )
        self.refresh()

    @Slot(bool)
    def setIncludeUnchanged(self, include_unchanged: bool) -> None:
        if bool(self._baselines.get("includeUnchanged", False)) == include_unchanged:
            return
        self._set_baselines(
            {
                **self._baselines,
                "includeUnchanged": include_unchanged,
            }
        )
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self._set_activity_page(1)
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        normalized_value = (status_filter or "").strip() or "all"
        if normalized_value == self._selected_status_filter:
            return
        self._set_selected_status_filter(normalized_value)
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
        normalized_value = (activity_id or "").strip()
        if normalized_value == self._selected_activity_id:
            return
        self._set_selected_activity_id(normalized_value)

    @Slot(str)
    def activateActivity(self, activity_id: str) -> None:
        self.selectActivity(activity_id)
        QTimer.singleShot(0, self.refresh)

    @Slot(int)
    def setActivityPage(self, page: int) -> None:
        resolved_page = max(1, int(page or 1))
        if resolved_page == self._activity_page:
            return
        self._set_activity_page(resolved_page)
        self.refresh()

    @Slot(int)
    def setActivityPageSize(self, page_size: int) -> None:
        resolved_page_size = max(10, int(page_size or 25))
        if resolved_page_size == self._activity_page_size:
            return
        self._set_activity_page_size(resolved_page_size)
        self._set_activity_page(1)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def saveCalendar(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.save_calendar(
                dict(payload)
            ),
            success_message="Working calendar updated.",
            activity_title="Working calendar updated",
            activity_status="Success",
            activity_meta="Calendar controls saved",
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addHoliday(self, payload: dict[str, object]) -> dict[str, object]:
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.add_holiday(
                dict(payload)
            ),
            success_message="Non-working day added.",
            activity_title="Holiday added",
            activity_status="Success",
            activity_meta=str(payload.get("holidayDate", "") or ""),
        )

    @Slot(str, result="QVariantMap")
    def deleteHoliday(self, holiday_id: str) -> dict[str, object]:
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.delete_holiday(
                holiday_id
            ),
            success_message="Non-working day removed.",
            activity_title="Holiday removed",
            activity_status="Warning",
            activity_meta=str(holiday_id or ""),
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createBaseline(self, payload: dict[str, object]) -> dict[str, object]:
        baseline_name = str(payload.get("name", "") or "Baseline").strip() or "Baseline"

        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.create_baseline(
                dict(payload)
            ),
            success_message="Baseline created.",
            activity_title=f'Baseline "{baseline_name}" saved',
            activity_status="Success",
            activity_meta=self._selected_project_id or "Current project",
        )

    @Slot(str, result="QVariantMap")
    def deleteBaseline(self, baseline_id: str) -> dict[str, object]:
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.delete_baseline(
                baseline_id
            ),
            success_message="Baseline deleted.",
            activity_title="Baseline removed",
            activity_status="Warning",
            activity_meta=str(baseline_id or ""),
        )

    @Slot(result="QVariantMap")
    def recalculateSchedule(self) -> dict[str, object]:
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.recalculate_schedule(
                self._selected_project_id
            ),
            success_message="Schedule recalculated.",
            activity_title="Schedule recalculated",
            activity_status="Success",
            activity_meta=self._selected_project_id or "Current project",
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        related_name = str(payload.get("relatedActivityName", "") or "").strip()
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.create_dependency(
                dict(payload)
            ),
            success_message="Dependency created.",
            activity_title="Dependency created",
            activity_status="Success",
            activity_meta=related_name or "Activity relationship saved",
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        related_name = str(payload.get("relatedActivityName", "") or "").strip()
        lag_label = str(payload.get("lagDays", "") or "").strip()
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.update_dependency(
                dict(payload)
            ),
            success_message="Dependency updated.",
            activity_title="Dependency updated",
            activity_status="Success",
            activity_meta=f"{related_name or 'Linked activity'} | Lag {lag_label or '0'}",
        )

    @Slot(str, result="QVariantMap")
    def deleteDependency(self, dependency_id: str) -> dict[str, object]:
        return self._run_planning_mutation(
            operation=lambda: self._scheduling_workspace_presenter.delete_dependency(
                dependency_id
            ),
            success_message="Dependency removed.",
            activity_title="Dependency removed",
            activity_status="Warning",
            activity_meta=str(dependency_id or ""),
        )

    @Slot("QVariantMap", result="QVariantMap")
    def calculateWorkingDays(self, payload: dict[str, object]) -> dict[str, object]:
        self._set_error_message("")
        try:
            result = self._scheduling_workspace_presenter.calculate_working_days(
                dict(payload)
            )
        except Exception as exc:
            self._set_calculator_result("")
            self._set_feedback_message("")
            self._set_error_message(str(exc))
            return {"ok": False, "message": str(exc)}
        self._set_calculator_result(result)
        self._set_feedback_message("")
        self._record_activity(
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
        self._record_activity(
            title="Schedule export requested",
            status_label="Info",
            subtitle="Export adapter pending",
            meta_text=self._selected_project_id or "Current project",
        )
        self.refresh()
        return {"ok": True, "message": message}

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "project_baseline",
            "resource",
            scope_code="project_management",
        )

    def _run_planning_mutation(
        self,
        *,
        operation,
        success_message: str,
        activity_title: str,
        activity_status: str,
        activity_meta: str,
    ) -> dict[str, object]:
        return run_mutation(
            operation=operation,
            success_message=success_message,
            on_success=lambda: self._after_planning_mutation(
                activity_title=activity_title,
                activity_status=activity_status,
                activity_meta=activity_meta,
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _after_planning_mutation(
        self,
        *,
        activity_title: str,
        activity_status: str,
        activity_meta: str,
    ) -> None:
        self._record_activity(
            title=activity_title,
            status_label=activity_status,
            subtitle=self._selected_project_id or "Current project",
            meta_text=activity_meta,
        )
        self.refresh()

    def _record_activity(
        self,
        *,
        title: str,
        status_label: str,
        subtitle: str,
        meta_text: str,
    ) -> None:
        if not title.strip():
            return
        self._activity_log = [
            {
                "title": title.strip(),
                "statusLabel": status_label.strip() or "Info",
                "subtitle": subtitle.strip(),
                "metaText": meta_text.strip(),
            },
            *self._activity_log[:11],
        ]

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: list[dict[str, str]]) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_calendar_options(self, calendar_options: list[dict[str, str]]) -> None:
        if calendar_options == self._calendar_options:
            return
        self._calendar_options = calendar_options
        self.calendarOptionsChanged.emit()

    def _set_baseline_options(self, baseline_options: list[dict[str, str]]) -> None:
        if baseline_options == self._baseline_options:
            return
        self._baseline_options = baseline_options
        self.baselineOptionsChanged.emit()

    def _set_dependency_type_options(
        self, dependency_type_options: list[dict[str, str]]
    ) -> None:
        if dependency_type_options == self._dependency_type_options:
            return
        self._dependency_type_options = dependency_type_options
        self.dependencyTypeOptionsChanged.emit()

    def _set_dependency_task_options(
        self, dependency_task_options: list[dict[str, str]]
    ) -> None:
        if dependency_task_options == self._dependency_task_options:
            return
        self._dependency_task_options = dependency_task_options
        self.dependencyTaskOptionsChanged.emit()

    def _set_status_options(self, status_options: list[dict[str, str]]) -> None:
        if status_options == self._status_options:
            return
        self._status_options = status_options
        self.statusOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_selected_calendar_id(self, selected_calendar_id: str) -> None:
        if selected_calendar_id == self._selected_calendar_id:
            return
        self._selected_calendar_id = selected_calendar_id
        self.selectedCalendarIdChanged.emit()

    def _set_selected_baseline_id(self, selected_baseline_id: str) -> None:
        if selected_baseline_id == self._selected_baseline_id:
            return
        self._selected_baseline_id = selected_baseline_id
        self.selectedBaselineIdChanged.emit()

    def _set_selected_status_filter(self, selected_status_filter: str) -> None:
        if selected_status_filter == self._selected_status_filter:
            return
        self._selected_status_filter = selected_status_filter
        self.selectedStatusFilterChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_show_critical_only(self, value: bool) -> None:
        if value == self._show_critical_only:
            return
        self._show_critical_only = value
        self.showCriticalOnlyChanged.emit()

    def _set_show_delayed_only(self, value: bool) -> None:
        if value == self._show_delayed_only:
            return
        self._show_delayed_only = value
        self.showDelayedOnlyChanged.emit()

    def _set_activity_page(self, value: int) -> None:
        if value == self._activity_page:
            return
        self._activity_page = value
        self.activityPageChanged.emit()

    def _set_activity_page_size(self, value: int) -> None:
        if value == self._activity_page_size:
            return
        self._activity_page_size = value
        self.activityPageSizeChanged.emit()

    def _set_activity_total_count(self, value: int) -> None:
        if value == self._activity_total_count:
            return
        self._activity_total_count = value
        self.activityTotalCountChanged.emit()

    def _set_selected_activity_id(self, selected_activity_id: str) -> None:
        if selected_activity_id == self._selected_activity_id:
            return
        self._selected_activity_id = selected_activity_id
        self.selectedActivityIdChanged.emit()

    def _set_calendar(self, calendar: dict[str, object]) -> None:
        if calendar == self._calendar:
            return
        self._calendar = calendar
        self.calendarChanged.emit()

    def _set_baselines(self, baselines: dict[str, object]) -> None:
        if baselines == self._baselines:
            return
        self._baselines = baselines
        self.baselinesChanged.emit()

    def _set_schedule(self, schedule: dict[str, object]) -> None:
        if schedule == self._schedule:
            return
        self._schedule = schedule
        self.scheduleChanged.emit()

    def _set_timeline(self, timeline: dict[str, object]) -> None:
        if timeline == self._timeline:
            return
        self._timeline = timeline
        self.timelineChanged.emit()

    def _set_critical_path(self, critical_path: dict[str, object]) -> None:
        if critical_path == self._critical_path:
            return
        self._critical_path = critical_path
        self.criticalPathChanged.emit()

    def _set_diagnostics(self, diagnostics: dict[str, object]) -> None:
        if diagnostics == self._diagnostics:
            return
        self._diagnostics = diagnostics
        self.diagnosticsChanged.emit()

    def _set_delayed_activities(self, delayed_activities: dict[str, object]) -> None:
        if delayed_activities == self._delayed_activities:
            return
        self._delayed_activities = delayed_activities
        self.delayedActivitiesChanged.emit()

    def _set_resource_loading(self, resource_loading: dict[str, object]) -> None:
        if resource_loading == self._resource_loading:
            return
        self._resource_loading = resource_loading
        self.resourceLoadingChanged.emit()

    def _set_baseline_register(self, baseline_register: dict[str, object]) -> None:
        if baseline_register == self._baseline_register:
            return
        self._baseline_register = baseline_register
        self.baselineRegisterChanged.emit()

    def _set_dependencies(self, dependencies: dict[str, object]) -> None:
        if dependencies == self._dependencies:
            return
        self._dependencies = dependencies
        self.dependenciesChanged.emit()

    def _set_constraints(self, constraints: dict[str, object]) -> None:
        if constraints == self._constraints:
            return
        self._constraints = constraints
        self.constraintsChanged.emit()

    def _set_activity_feed(self, activity_feed: dict[str, object]) -> None:
        if activity_feed == self._activity_feed:
            return
        self._activity_feed = activity_feed
        self.activityFeedChanged.emit()

    def _set_selected_activity(self, selected_activity: dict[str, object]) -> None:
        if selected_activity == self._selected_activity:
            return
        self._selected_activity = selected_activity
        self.selectedActivityChanged.emit()

    def _set_calculator_result(self, calculator_result: str) -> None:
        if calculator_result == self._calculator_result:
            return
        self._calculator_result = calculator_result
        self.calculatorResultChanged.emit()


__all__ = ["ProjectManagementSchedulingWorkspaceController"]
