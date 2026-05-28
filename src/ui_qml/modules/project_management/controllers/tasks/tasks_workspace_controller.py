from __future__ import annotations

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.tasks.pm_assignment_controller import (
    PMAssignmentController,
)
from src.ui_qml.modules.project_management.controllers.tasks.pm_collaboration_controller import (
    PMCollaborationController,
)
from src.ui_qml.modules.project_management.controllers.tasks.pm_dependency_controller import (
    PMDependencyController,
)
from src.ui_qml.modules.project_management.controllers.tasks.pm_task_list_controller import (
    PMTaskListController,
)
from src.ui_qml.modules.project_management.controllers.tasks.pm_time_controller import (
    PMTimeController,
)
from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
    ProjectManagementWorkspaceControllerBase,
    serialize_task_record_view_models,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectTasksWorkspacePresenter,
)

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


class _TaskDetailWorkerSignals(QObject):
    finished = Signal(object)  # emits (request_id: int, workspace_state)
    failed = Signal(object)    # emits (request_id: int, error_message: str)


class _TaskDetailWorker(QRunnable):
    """Runs build_task_basic_detail_state in a thread-pool thread."""

    def __init__(
        self,
        *,
        presenter: ProjectTasksWorkspacePresenter,
        task_id: str,
        project_id: str | None,
        request_id: int,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._signals = _TaskDetailWorkerSignals()
        self._presenter = presenter
        self._task_id = task_id
        self._project_id = project_id
        self._request_id = request_id

    @property
    def signals(self) -> _TaskDetailWorkerSignals:
        return self._signals

    def run(self) -> None:
        try:
            ws = self._presenter.build_task_basic_detail_state(
                task_id=self._task_id,
                project_id=self._project_id,
            )
            self._signals.finished.emit((self._request_id, ws))
        except Exception as exc:
            self._signals.failed.emit((self._request_id, str(exc)))


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementTasksWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    # ── Signals ──────────────────────────────────────────────────────
    taskPageChanged = Signal()
    taskPageSizeChanged = Signal()
    taskTotalCountChanged = Signal()
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    statusOptionsChanged = Signal()
    bulkStatusOptionsChanged = Signal()
    priorityOptionsChanged = Signal()
    scheduleOptionsChanged = Signal()
    taskViewOptionsChanged = Signal()
    selectedStatusFilterChanged = Signal()
    selectedPriorityFilterChanged = Signal()
    selectedScheduleFilterChanged = Signal()
    selectedTaskViewNameChanged = Signal()
    searchTextChanged = Signal()
    tasksChanged = Signal()
    selectedTaskChanged = Signal()
    selectedTaskIdChanged = Signal()
    selectedTaskIdsChanged = Signal()
    selectedTaskCountChanged = Signal()
    selectedTaskDoneCountChanged = Signal()
    taskActionHistoryChanged = Signal()
    assignmentOptionsChanged = Signal()
    selectedAssignmentIdChanged = Signal()
    dependencyTaskOptionsChanged = Signal()
    dependencyTypeOptionsChanged = Signal()
    assignmentsChanged = Signal()
    dependenciesChanged = Signal()
    timeAssignmentOptionsChanged = Signal()
    timePeriodOptionsChanged = Signal()
    selectedTimePeriodStartChanged = Signal()
    timeAssignmentSummaryChanged = Signal()
    timeEntriesChanged = Signal()
    timeSectionLoadedChanged = Signal()
    selectedTimeEntryIdChanged = Signal()
    selectedTimeEntryChanged = Signal()
    collaborationMentionOptionsChanged = Signal()
    collaborationDocumentOptionsChanged = Signal()
    collaborationCommentsChanged = Signal()
    collaborationPresenceChanged = Signal()
    collaborationSectionLoadedChanged = Signal()
    taskSkillRequirementsChanged = Signal()
    skillRequirementsSectionLoadedChanged = Signal()
    scheduleImpactChanged = Signal()
    scheduleImpactSectionLoadedChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        tasks_workspace_presenter: ProjectTasksWorkspacePresenter | None = None,
        task_view_store: ProjectManagementTaskViewStore | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.tasks"
        )
        self._tasks_workspace_presenter = (
            tasks_workspace_presenter or ProjectTasksWorkspacePresenter()
        )
        # ── Pagination state ───────────────────────────────────────────
        self._task_page = 1
        self._task_page_size = 25
        self._task_total_count = 0
        # ── Coordinator / navigation state ────────────────────────────
        self._selected_project_id = ""
        self._selected_status_filter = "all"
        self._selected_priority_filter = "all"
        self._selected_schedule_filter = "all"
        self._search_text = ""
        self._selected_task_view_name = ""
        self._selected_task_id = ""
        self._selected_assignment_id = ""
        self._selected_time_period_start = ""
        self._selected_time_entry_id = ""
        self._task_review_active = False
        self._task_activation_request_id = 0
        self._time_section_loaded_for_task_id = ""
        self._collaboration_section_loaded_for_task_id = ""
        self._assignments_section_loaded_for_task_id = ""
        self._dependencies_section_loaded_for_task_id = ""
        self._skill_requirements_section_loaded_for_task_id = ""
        self._schedule_impact_section_loaded_for_task_id = ""
        self._schedule_impact: dict[str, object] = {}
        # ── Saved views ────────────────────────────────────────────────
        self._task_view_store = task_view_store or ProjectManagementTaskViewStore()
        self._saved_task_views: dict[str, dict[str, object]] = (
            self._load_saved_task_views()
        )
        self._task_view_options: list[dict[str, str]] = []
        self._refresh_task_view_options()
        # ── Sub-controllers ────────────────────────────────────────────
        _cb = dict(
            presenter=self._tasks_workspace_presenter,
            facade_refresh=self._request_domain_refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
            parent=self,
        )
        self._task_list = PMTaskListController(**_cb)
        self._assignments_ctrl = PMAssignmentController(**_cb)
        self._dependencies_ctrl = PMDependencyController(**_cb)
        self._time_ctrl = PMTimeController(
            **_cb,
            refresh_time_entries=self._refresh_time_entries_only,
        )
        self._collab_ctrl = PMCollaborationController(**_cb)
        # Connect sub-controller signals → facade signals (backward compat)
        self._task_list.overviewChanged.connect(self.overviewChanged)
        self._task_list.projectOptionsChanged.connect(self.projectOptionsChanged)
        self._task_list.statusOptionsChanged.connect(self.statusOptionsChanged)
        self._task_list.bulkStatusOptionsChanged.connect(self.bulkStatusOptionsChanged)
        self._task_list.priorityOptionsChanged.connect(self.priorityOptionsChanged)
        self._task_list.scheduleOptionsChanged.connect(self.scheduleOptionsChanged)
        self._task_list.tasksChanged.connect(self.tasksChanged)
        self._task_list.selectedTaskChanged.connect(self.selectedTaskChanged)
        self._task_list.selectedTaskIdsChanged.connect(self.selectedTaskIdsChanged)
        self._task_list.selectedTaskCountChanged.connect(self.selectedTaskCountChanged)
        self._task_list.selectedTaskDoneCountChanged.connect(
            self.selectedTaskDoneCountChanged
        )
        self._task_list.taskActionHistoryChanged.connect(self.taskActionHistoryChanged)
        self._assignments_ctrl.assignmentOptionsChanged.connect(
            self.assignmentOptionsChanged
        )
        self._assignments_ctrl.assignmentsChanged.connect(self.assignmentsChanged)
        self._dependencies_ctrl.dependencyTaskOptionsChanged.connect(
            self.dependencyTaskOptionsChanged
        )
        self._dependencies_ctrl.dependencyTypeOptionsChanged.connect(
            self.dependencyTypeOptionsChanged
        )
        self._dependencies_ctrl.dependenciesChanged.connect(self.dependenciesChanged)
        self._time_ctrl.timeAssignmentOptionsChanged.connect(
            self.timeAssignmentOptionsChanged
        )
        self._time_ctrl.timePeriodOptionsChanged.connect(self.timePeriodOptionsChanged)
        self._time_ctrl.timeAssignmentSummaryChanged.connect(
            self.timeAssignmentSummaryChanged
        )
        self._time_ctrl.timeEntriesChanged.connect(self.timeEntriesChanged)
        self._time_ctrl.selectedTimeEntryChanged.connect(self.selectedTimeEntryChanged)
        self._collab_ctrl.collaborationMentionOptionsChanged.connect(
            self.collaborationMentionOptionsChanged
        )
        self._collab_ctrl.collaborationDocumentOptionsChanged.connect(
            self.collaborationDocumentOptionsChanged
        )
        self._collab_ctrl.collaborationCommentsChanged.connect(
            self.collaborationCommentsChanged
        )
        self._collab_ctrl.collaborationPresenceChanged.connect(
            self.collaborationPresenceChanged
        )
        self._assignments_ctrl.taskSkillRequirementsChanged.connect(
            self.taskSkillRequirementsChanged
        )
        self.destroyed.connect(self._collab_ctrl.on_destroyed_cleanup)
        self._bind_domain_events()
        self.refresh()

    # ── Sub-controller access ─────────────────────────────────────────

    @Property(QObject, constant=True)
    def taskListController(self) -> PMTaskListController:
        return self._task_list

    @Property(QObject, constant=True)
    def assignmentsController(self) -> PMAssignmentController:
        return self._assignments_ctrl

    @Property(QObject, constant=True)
    def dependenciesController(self) -> PMDependencyController:
        return self._dependencies_ctrl

    @Property(QObject, constant=True)
    def timeController(self) -> PMTimeController:
        return self._time_ctrl

    @Property(QObject, constant=True)
    def collaborationController(self) -> PMCollaborationController:
        return self._collab_ctrl

    # ── Backward-compat properties (delegate to sub-controllers) ─────

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._task_list.overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._task_list.projectOptions

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._task_list.statusOptions

    @Property("QVariantList", notify=bulkStatusOptionsChanged)
    def bulkStatusOptions(self) -> list[dict[str, str]]:
        return self._task_list.bulkStatusOptions

    @Property("QVariantList", notify=priorityOptionsChanged)
    def priorityOptions(self) -> list[dict[str, str]]:
        return self._task_list.priorityOptions

    @Property("QVariantList", notify=scheduleOptionsChanged)
    def scheduleOptions(self) -> list[dict[str, str]]:
        return self._task_list.scheduleOptions

    @Property("QVariantList", notify=taskViewOptionsChanged)
    def taskViewOptions(self) -> list[dict[str, str]]:
        return self._task_view_options

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=selectedPriorityFilterChanged)
    def selectedPriorityFilter(self) -> str:
        return self._selected_priority_filter

    @Property(str, notify=selectedScheduleFilterChanged)
    def selectedScheduleFilter(self) -> str:
        return self._selected_schedule_filter

    @Property(str, notify=selectedTaskViewNameChanged)
    def selectedTaskViewName(self) -> str:
        return self._selected_task_view_name

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=tasksChanged)
    def tasks(self) -> dict[str, object]:
        return self._task_list.tasks

    @Property("QVariantMap", notify=selectedTaskChanged)
    def selectedTask(self) -> dict[str, object]:
        return self._task_list.selectedTask

    @Property(str, notify=selectedTaskIdChanged)
    def selectedTaskId(self) -> str:
        return self._selected_task_id

    @Property("QVariantList", notify=selectedTaskIdsChanged)
    def selectedTaskIds(self) -> list[str]:
        return self._task_list.selectedTaskIds

    @Property(int, notify=selectedTaskCountChanged)
    def selectedTaskCount(self) -> int:
        return self._task_list.selectedTaskCount

    @Property(int, notify=selectedTaskDoneCountChanged)
    def selectedTaskDoneCount(self) -> int:
        return self._task_list.selectedTaskDoneCount

    @Property(bool, notify=taskActionHistoryChanged)
    def canUndoTaskAction(self) -> bool:
        return self._task_list.canUndoTaskAction

    @Property(bool, notify=taskActionHistoryChanged)
    def canRedoTaskAction(self) -> bool:
        return self._task_list.canRedoTaskAction

    @Property(str, notify=taskActionHistoryChanged)
    def nextUndoLabel(self) -> str:
        return self._task_list.nextUndoLabel

    @Property(str, notify=taskActionHistoryChanged)
    def nextRedoLabel(self) -> str:
        return self._task_list.nextRedoLabel

    @Property("QVariantList", notify=assignmentOptionsChanged)
    def assignmentOptions(self) -> list[dict[str, str]]:
        return self._assignments_ctrl.assignmentOptions

    @Property(str, notify=selectedAssignmentIdChanged)
    def selectedAssignmentId(self) -> str:
        return self._selected_assignment_id

    @Property("QVariantList", notify=dependencyTaskOptionsChanged)
    def dependencyTaskOptions(self) -> list[dict[str, str]]:
        return self._dependencies_ctrl.dependencyTaskOptions

    @Property("QVariantList", notify=dependencyTypeOptionsChanged)
    def dependencyTypeOptions(self) -> list[dict[str, str]]:
        return self._dependencies_ctrl.dependencyTypeOptions

    @Property("QVariantMap", notify=assignmentsChanged)
    def assignments(self) -> dict[str, object]:
        return self._assignments_ctrl.assignments

    @Property("QVariantMap", notify=dependenciesChanged)
    def dependencies(self) -> dict[str, object]:
        return self._dependencies_ctrl.dependencies

    @Property("QVariantList", notify=timeAssignmentOptionsChanged)
    def timeAssignmentOptions(self) -> list[dict[str, str]]:
        return self._time_ctrl.timeAssignmentOptions

    @Property("QVariantList", notify=timePeriodOptionsChanged)
    def timePeriodOptions(self) -> list[dict[str, str]]:
        return self._time_ctrl.timePeriodOptions

    @Property(str, notify=selectedTimePeriodStartChanged)
    def selectedTimePeriodStart(self) -> str:
        return self._selected_time_period_start

    @Property("QVariantMap", notify=timeAssignmentSummaryChanged)
    def timeAssignmentSummary(self) -> dict[str, object]:
        return self._time_ctrl.timeAssignmentSummary

    @Property("QVariantMap", notify=timeEntriesChanged)
    def timeEntries(self) -> dict[str, object]:
        return self._time_ctrl.timeEntries

    @Property(str, notify=selectedTimeEntryIdChanged)
    def selectedTimeEntryId(self) -> str:
        return self._selected_time_entry_id

    @Property("QVariantMap", notify=selectedTimeEntryChanged)
    def selectedTimeEntry(self) -> dict[str, object]:
        return self._time_ctrl.selectedTimeEntry

    @Property("QVariantList", notify=collaborationMentionOptionsChanged)
    def collaborationMentionOptions(self) -> list[dict[str, str]]:
        return self._collab_ctrl.collaborationMentionOptions

    @Property("QVariantList", notify=collaborationDocumentOptionsChanged)
    def collaborationDocumentOptions(self) -> list[dict[str, str]]:
        return self._collab_ctrl.collaborationDocumentOptions

    @Property("QVariantMap", notify=collaborationCommentsChanged)
    def collaborationComments(self) -> dict[str, object]:
        return self._collab_ctrl.collaborationComments

    @Property("QVariantMap", notify=collaborationPresenceChanged)
    def collaborationPresence(self) -> dict[str, object]:
        return self._collab_ctrl.collaborationPresence

    @Property(bool, notify=timeSectionLoadedChanged)
    def isTimeSectionLoaded(self) -> bool:
        return (
            bool(self._selected_task_id)
            and self._time_section_loaded_for_task_id == self._selected_task_id
        )

    @Property(bool, notify=collaborationSectionLoadedChanged)
    def isCollaborationSectionLoaded(self) -> bool:
        return (
            bool(self._selected_task_id)
            and self._collaboration_section_loaded_for_task_id == self._selected_task_id
        )

    @Property("QVariantMap", notify=taskSkillRequirementsChanged)
    def taskSkillRequirements(self) -> dict[str, object]:
        return self._assignments_ctrl.taskSkillRequirements

    @Property(bool, notify=skillRequirementsSectionLoadedChanged)
    def isSkillRequirementsSectionLoaded(self) -> bool:
        return (
            bool(self._selected_task_id)
            and self._skill_requirements_section_loaded_for_task_id == self._selected_task_id
        )

    @Property("QVariantMap", notify=scheduleImpactChanged)
    def scheduleImpact(self) -> dict[str, object]:
        return self._schedule_impact

    @Property(bool, notify=scheduleImpactSectionLoadedChanged)
    def isScheduleImpactSectionLoaded(self) -> bool:
        return (
            bool(self._selected_task_id)
            and self._schedule_impact_section_loaded_for_task_id == self._selected_task_id
        )

    # ── Pagination properties ─────────────────────────────────────────

    @Property(int, notify=taskPageChanged)
    def taskPage(self) -> int:
        return self._task_page

    @Property(int, notify=taskPageSizeChanged)
    def taskPageSize(self) -> int:
        return self._task_page_size

    @Property(int, notify=taskTotalCountChanged)
    def taskTotalCount(self) -> int:
        return self._task_total_count

    def _set_task_page(self, v: int) -> None:
        if v == self._task_page:
            return
        self._task_page = v
        self.taskPageChanged.emit()

    def _set_task_page_size(self, v: int) -> None:
        if v == self._task_page_size:
            return
        self._task_page_size = v
        self.taskPageSizeChanged.emit()

    def _set_task_total_count(self, v: int) -> None:
        if v == self._task_total_count:
            return
        self._task_total_count = v
        self.taskTotalCountChanged.emit()

    # ── Refresh ───────────────────────────────────────────────────────

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
            ws = self._tasks_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id or None,
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                priority_filter=self._selected_priority_filter,
                schedule_filter=self._selected_schedule_filter,
                selected_task_id=self._selected_task_id or None,
                selected_assignment_id=self._selected_assignment_id or None,
                selected_time_period_start=self._selected_time_period_start,
                selected_time_entry_id=self._selected_time_entry_id or None,
                page=self._task_page,
                page_size=self._task_page_size,
            )
            self._task_list._update(ws)
            self._set_selected_task_id(ws.selected_task_id)
            self._set_selected_project_id(ws.selected_project_id)
            self._set_selected_status_filter(ws.selected_status_filter)
            self._set_selected_priority_filter(ws.selected_priority_filter)
            self._set_selected_schedule_filter(ws.selected_schedule_filter)
            self._set_search_text(ws.search_text)
            
            self._set_empty_state(ws.empty_state)
            self._set_task_total_count(ws.total_count)
            self._set_task_page(ws.page)
            self._set_task_page_size(ws.page_size)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

    # ── Selection / navigation slots ──────────────────────────────────

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        normalized = (project_id or "").strip()
        if normalized == self._selected_project_id:
            return
        self._set_selected_project_id(normalized)
        self._set_selected_task_id("")
        self._set_selected_assignment_id("")
        self._set_selected_time_period_start("")
        self._set_selected_time_entry_id("")
        self._task_page = 1
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized = (search_text or "").strip()
        if normalized == self._search_text:
            return
        self._set_search_text(normalized)
        self._set_selected_task_view_name("")
        self._task_page = 1
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        normalized = (status_filter or "").strip().lower() or "all"
        if normalized == self._selected_status_filter.lower():
            return
        self._set_selected_status_filter(normalized)
        self._set_selected_task_view_name("")
        self._task_page = 1
        self.refresh()

    @Slot(str)
    def setPriorityFilter(self, priority_filter: str) -> None:
        normalized = (priority_filter or "").strip().lower() or "all"
        if normalized == self._selected_priority_filter.lower():
            return
        self._set_selected_priority_filter(normalized)
        self._set_selected_task_view_name("")
        self._task_page = 1
        self.refresh()

    @Slot(str)
    def setScheduleFilter(self, schedule_filter: str) -> None:
        normalized = (schedule_filter or "").strip().lower() or "all"
        if normalized == self._selected_schedule_filter.lower():
            return
        self._set_selected_schedule_filter(normalized)
        self._set_selected_task_view_name("")
        self._task_page = 1
        self.refresh()

    @Slot()
    def clearFilters(self) -> None:
        if (
            not self._search_text
            and self._selected_status_filter == "all"
            and self._selected_priority_filter == "all"
            and self._selected_schedule_filter == "all"
            and not self._selected_task_view_name
        ):
            return
        self._set_search_text("")
        self._set_selected_status_filter("all")
        self._set_selected_priority_filter("all")
        self._set_selected_schedule_filter("all")
        self._set_selected_task_view_name("")
        self._task_page = 1
        self.refresh()

    @Slot(str)
    def selectTask(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if normalized == self._selected_task_id:
            return
        self._set_selected_task_id(normalized)
        self._reset_task_lazy_sections()

    @Slot(int)
    def setTaskPage(self, page: int) -> None:
        p = max(1, page)
        if p == self._task_page:
            return
        self._set_task_page(p)
        self.refresh()

    @Slot(int)
    def setTaskPageSize(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._task_page_size:
            return
        self._task_page_size = page_size
        self.taskPageSizeChanged.emit()
        self._set_task_page(1)
        self.refresh()

    @Slot(str)
    def activateTask(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if not normalized:
            return

        # ── Reset state then show in-memory preview (0 API calls) ────
        self._set_selected_task_id(normalized)
        self._reset_task_lazy_sections()
        self._task_list.selectTaskPreview(normalized)

        # ── Stage 2: full basic detail in background thread ───────────
        self._set_is_loading(True)
        self._set_error_message("")
        self._task_activation_request_id += 1
        req_id = self._task_activation_request_id

        worker = _TaskDetailWorker(
            presenter=self._tasks_workspace_presenter,
            task_id=normalized,
            project_id=self._selected_project_id or None,
            request_id=req_id,
        )
        worker.signals.finished.connect(self._on_task_detail_loaded)
        worker.signals.failed.connect(self._on_task_detail_error)
        QThreadPool.globalInstance().start(worker)

    def _on_task_detail_loaded(self, data: object) -> None:
        try:
            request_id, ws = data  # type: ignore[misc]
        except (TypeError, ValueError):
            return
        if request_id != self._task_activation_request_id:
            return  # stale result from a superseded task click
        self._task_list.updateSelectedTaskOnly(ws)
        self._set_selected_task_id(ws.selected_task_id)
        self._set_is_loading(False)

    def _on_task_detail_error(self, data: object) -> None:
        try:
            request_id, message = data  # type: ignore[misc]
        except (TypeError, ValueError):
            return
        if request_id != self._task_activation_request_id:
            return
        self._set_error_message(str(message))
        self._set_is_loading(False)

    @Slot()
    def loadTaskAssignmentsAndDependencies(self) -> None:
        self.loadSelectedTaskAssignments()
        self.loadSelectedTaskDependencies()

    @Slot()
    def loadSelectedTaskAssignments(self) -> None:
        if not self._selected_task_id:
            return
        if self._assignments_section_loaded_for_task_id == self._selected_task_id:
            return
        self._set_is_loading(True)
        try:
            self._clear_section_error("assignments")
            ws = self._tasks_workspace_presenter.build_task_assignments_state(
                task_id=self._selected_task_id,
                project_id=self._selected_project_id or None,
            )
            self._assignments_ctrl._update(ws)
            self._assignments_section_loaded_for_task_id = self._selected_task_id
            if not self._selected_assignment_id:
                assignment_items = getattr(ws.assignments, "items", ()) or ()
                if assignment_items:
                    first = assignment_items[0]
                    self._set_selected_assignment_id(str(getattr(first, "id", "") or ""))
        except Exception as exc:
            self._set_section_error("assignments", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadSelectedTaskDependencies(self) -> None:
        if not self._selected_task_id:
            return
        if self._dependencies_section_loaded_for_task_id == self._selected_task_id:
            return
        self._set_is_loading(True)
        try:
            self._clear_section_error("dependencies")
            ws = self._tasks_workspace_presenter.build_task_dependencies_state(
                task_id=self._selected_task_id,
                project_id=self._selected_project_id or None,
            )
            self._dependencies_ctrl._update(ws)
            self._dependencies_section_loaded_for_task_id = self._selected_task_id
        except Exception as exc:
            self._set_section_error("dependencies", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadSelectedTaskTime(self) -> None:
        if not self._selected_task_id:
            return

        self._set_is_loading(True)

        try:
            self._clear_section_error("time")

            ws = self._tasks_workspace_presenter.build_task_time_state(
                task_id=self._selected_task_id,
                selected_assignment_id=self._selected_assignment_id or None,
                selected_time_period_start=self._selected_time_period_start,
                selected_time_entry_id=self._selected_time_entry_id or None,
            )

            self._time_ctrl._update(ws)

            self._set_selected_assignment_id(ws.selected_assignment_id)
            self._set_selected_time_period_start(ws.selected_time_period_start)
            self._set_selected_time_entry_id(ws.selected_time_entry_id)

            self._set_time_section_loaded_for_task_id(self._selected_task_id)

        except Exception as exc:
            self._set_section_error("time", str(exc))

        finally:
            self._set_is_loading(False)
        
    @Slot()
    def loadSelectedTaskCollaboration(self) -> None:
        if not self._selected_task_id:
            return

        if self.isCollaborationSectionLoaded:
            return

        self._set_is_loading(True)

        try:
            self._clear_section_error("activity")

            ws = self._tasks_workspace_presenter.build_task_collaboration_state(
                task_id=self._selected_task_id,
            )

            self._collab_ctrl._update(ws)

            self._set_collaboration_section_loaded_for_task_id(
                self._selected_task_id
            )

        except Exception as exc:
            self._set_section_error("activity", str(exc))

        finally:
            self._set_is_loading(False)

    @Slot()
    def loadSelectedTaskSkillRequirements(self) -> None:
        if not self._selected_task_id:
            return
        if self._skill_requirements_section_loaded_for_task_id == self._selected_task_id:
            return
        self._set_is_loading(True)
        try:
            self._clear_section_error("skills")
            ws = self._tasks_workspace_presenter.build_task_skill_requirements_state(
                task_id=self._selected_task_id,
            )
            self._assignments_ctrl._update_skill_requirements(ws)
            self._skill_requirements_section_loaded_for_task_id = self._selected_task_id
        except Exception as exc:
            self._set_section_error("skills", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot()
    def loadSelectedTaskScheduleImpact(self) -> None:
        if not self._selected_task_id:
            return
        if self._schedule_impact_section_loaded_for_task_id == self._selected_task_id:
            return
        self._set_is_loading(True)
        try:
            self._clear_section_error("scheduleImpact")
            impact = self._tasks_workspace_presenter.build_task_schedule_impact_state(
                task_id=self._selected_task_id,
                project_id=self._selected_project_id or None,
            )
            self._set_schedule_impact(impact)
            self._schedule_impact_section_loaded_for_task_id = self._selected_task_id
        except Exception as exc:
            self._set_section_error("scheduleImpact", str(exc))
        finally:
            self._set_is_loading(False)

    @Slot(bool)
    def setTaskReviewActive(self, active: bool) -> None:
        normalized = bool(active)
        if normalized == self._task_review_active:
            return
        self._task_review_active = normalized
        self._collab_ctrl.sync_review_presence(
            self._selected_task_id if normalized else ""
        )

    @Slot(str, bool)
    def setTaskBulkSelection(self, task_id: str, selected: bool) -> None:
        self._task_list.setTaskBulkSelection(task_id, selected)

    @Slot()
    def selectVisibleTasks(self) -> None:
        self._task_list.selectVisibleTasks()

    @Slot()
    def clearTaskBulkSelection(self) -> None:
        self._task_list.clearTaskBulkSelection()

    @Slot(str)
    def selectAssignment(self, assignment_id: str) -> None:
        normalized = (assignment_id or "").strip()
        if normalized == self._selected_assignment_id:
            return

        self._set_selected_assignment_id(normalized)
        self._set_selected_time_period_start("")
        self._set_selected_time_entry_id("")
        self._set_time_section_loaded_for_task_id("")

        if normalized:
            self.loadSelectedTaskTime()

    @Slot(str)
    def selectTimePeriod(self, period_start: str) -> None:
        normalized = (period_start or "").strip()
        if normalized == self._selected_time_period_start:
            return

        self._set_selected_time_period_start(normalized)
        self._set_selected_time_entry_id("")
        self._set_time_section_loaded_for_task_id("")

        self.loadSelectedTaskTime()

    @Slot(str)
    def selectTimeEntry(self, entry_id: str) -> None:
        normalized = (entry_id or "").strip()
        if normalized == self._selected_time_entry_id:
            return

        self._set_selected_time_entry_id(normalized)
        self._set_time_section_loaded_for_task_id("")

        self.loadSelectedTaskTime()
    # ── Saved views ───────────────────────────────────────────────────

    @Slot(str)
    def selectTaskView(self, view_name: str) -> None:
        self._set_selected_task_view_name((view_name or "").strip())

    @Slot(str, result="QVariantMap")
    def saveCurrentTaskView(self, view_name: str) -> dict[str, object]:
        normalized = (view_name or "").strip()
        if not normalized:
            self._set_error_message("Saved view name is required.")
            return {"ok": False, "message": "Saved view name is required."}
        self._saved_task_views[normalized] = self._capture_task_view_state()
        self._persist_saved_task_views()
        self._refresh_task_view_options()
        self._set_selected_task_view_name(normalized)
        self._set_error_message("")
        self._set_feedback_message(f'Saved task view "{normalized}".')
        return {"ok": True, "message": f'Saved task view "{normalized}".'}

    @Slot(result="QVariantMap")
    def applySelectedTaskView(self) -> dict[str, object]:
        view_name = self._selected_task_view_name
        if not view_name:
            self.refresh()
            return {"ok": True, "message": "Current filters applied."}
        state = self._saved_task_views.get(view_name)
        if not isinstance(state, dict):
            self._set_error_message("Saved task view is no longer available.")
            return {"ok": False, "message": "Saved task view is no longer available."}
        self._apply_task_view_state(state, selected_view_name=view_name)
        self._set_error_message("")
        self._set_feedback_message(f'Applied task view "{view_name}".')
        return {"ok": True, "message": f'Applied task view "{view_name}".'}

    @Slot(result="QVariantMap")
    def deleteSelectedTaskView(self) -> dict[str, object]:
        view_name = self._selected_task_view_name
        if not view_name:
            self._set_error_message("Choose a saved task view first.")
            return {"ok": False, "message": "Choose a saved task view first."}
        self._saved_task_views.pop(view_name, None)
        self._persist_saved_task_views()
        self._refresh_task_view_options()
        self._set_selected_task_view_name("")
        self._set_error_message("")
        self._set_feedback_message(f'Deleted task view "{view_name}".')
        return {"ok": True, "message": f'Deleted task view "{view_name}".'}

    # ── Backward-compat mutation delegates ───────────────────────────

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTasks(self, columns: list, file_path: str) -> dict[str, object]:
        from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file
        self._set_error_message("")
        try:
            all_ws = self._tasks_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id or None,
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                priority_filter=self._selected_priority_filter,
                schedule_filter=self._selected_schedule_filter,
                selected_task_id=None,
                selected_assignment_id=None,
                selected_time_period_start=self._selected_time_period_start,
                selected_time_entry_id=None,
                page=1,
                page_size=99999,
            )
            rows = serialize_task_record_view_models(all_ws.tasks)
            result = export_to_file(rows, list(columns), (file_path or "").strip())
            if result.get("ok"):
                self._set_feedback_message(result.get("message", "Export complete."))
            else:
                self._set_error_message(result.get("error", "Export failed."))
            return result
        except Exception as exc:
            self._set_error_message(str(exc))
            return {"ok": False, "error": str(exc)}

    @Slot("QVariantMap", result="QVariantMap")
    def createTask(self, payload: dict[str, object]) -> dict[str, object]:
        return self._task_list.createTask(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTask(self, payload: dict[str, object]) -> dict[str, object]:
        return self._task_list.updateTask(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateProgress(self, payload: dict[str, object]) -> dict[str, object]:
        return self._task_list.updateProgress(payload)

    @Slot(str, result="QVariantMap")
    def deleteTask(self, task_id: str) -> dict[str, object]:
        return self._task_list.deleteTask(task_id)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        return self._task_list.applyBulkStatus(payload)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteTasks(self, task_ids: list[object]) -> dict[str, object]:
        return self._task_list.bulkDeleteTasks(task_ids)

    @Slot(result="QVariantMap")
    def undoLastTaskAction(self) -> dict[str, object]:
        return self._task_list.undoLastTaskAction()

    @Slot(result="QVariantMap")
    def redoLastTaskAction(self) -> dict[str, object]:
        return self._task_list.redoLastTaskAction()

    @Slot("QVariantMap", result="QVariantMap")
    def createAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._assignments_ctrl.createAssignment(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateAssignmentAllocation(
        self, payload: dict[str, object]
    ) -> dict[str, object]:
        return self._assignments_ctrl.updateAssignmentAllocation(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def setAssignmentHours(self, payload: dict[str, object]) -> dict[str, object]:
        return self._assignments_ctrl.setAssignmentHours(payload)

    @Slot(str, result="QVariantMap")
    def deleteAssignment(self, assignment_id: str) -> dict[str, object]:
        return self._assignments_ctrl.deleteAssignment(assignment_id)

    @Slot("QVariantMap", result="QVariantMap")
    @Slot("QVariantMap", result="QVariantMap")
    def validateAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._assignments_ctrl.validateAssignment(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return self._dependencies_ctrl.createDependency(payload)

    @Slot(str, result="QVariantMap")
    def deleteDependency(self, dependency_id: str) -> dict[str, object]:
        return self._dependencies_ctrl.deleteDependency(dependency_id)

    @Slot("QVariantMap", result="QVariantMap")
    def addTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return self._time_ctrl.addTaskTimeEntry(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return self._time_ctrl.updateTaskTimeEntry(payload)

    @Slot(str, result="QVariantMap")
    def deleteTaskTimeEntry(self, entry_id: str) -> dict[str, object]:
        return self._time_ctrl.deleteTaskTimeEntry(entry_id)

    @Slot("QVariantMap", result="QVariantMap")
    def submitTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._time_ctrl.submitTaskPeriod(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def lockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._time_ctrl.lockTaskPeriod(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def unlockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return self._time_ctrl.unlockTaskPeriod(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def postTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._collab_ctrl.postTaskComment(payload)

    @Slot(str, result="QVariantMap")
    def markTaskCollaborationRead(self, task_id: str) -> dict[str, object]:
        return self._collab_ctrl.markTaskCollaborationRead(task_id)

    @Slot(str, str, result="QVariantMap")
    def beginTaskPresence(self, task_id: str, activity: str) -> dict[str, object]:
        return self._collab_ctrl.beginTaskPresence(task_id, activity)

    @Slot(str, result="QVariantMap")
    def endTaskPresence(self, task_id: str) -> dict[str, object]:
        return self._collab_ctrl.endTaskPresence(task_id)

    # ── Time-entries scoped refresh ───────────────────────────────────

    def _refresh_time_entries_only(self) -> None:
        """Rebuild only the time-entries section after an entry-level mutation.

        Avoids the full workspace reload that _request_domain_refresh() triggers,
        so task selection, section indexes, and scroll positions are preserved.
        Period-level mutations (submit/lock/unlock) still call _request_domain_refresh.
        """
        try:
            ws = self._tasks_workspace_presenter.build_task_time_state(
                task_id=self._selected_task_id,
                selected_assignment_id=self._selected_assignment_id or None,
                selected_time_period_start=self._selected_time_period_start,
            )
            self._time_ctrl._update(ws)
        except Exception:  # noqa: BLE001 — scoped refresh failure must not mask user success
            pass

    # ── Domain event binding ──────────────────────────────────────────

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "resource",
            "timesheet_period",
            "task_collaboration",
            scope_code="project_management",
        )

    # ── Coordinator state setters ─────────────────────────────────────

    def _set_selected_project_id(self, v: str) -> None:
        if v == self._selected_project_id:
            return
        self._selected_project_id = v
        self.selectedProjectIdChanged.emit()

    def _set_selected_status_filter(self, v: str) -> None:
        if v == self._selected_status_filter:
            return
        self._selected_status_filter = v
        self.selectedStatusFilterChanged.emit()

    def _set_selected_priority_filter(self, v: str) -> None:
        if v == self._selected_priority_filter:
            return
        self._selected_priority_filter = v
        self.selectedPriorityFilterChanged.emit()

    def _set_selected_schedule_filter(self, v: str) -> None:
        if v == self._selected_schedule_filter:
            return
        self._selected_schedule_filter = v
        self.selectedScheduleFilterChanged.emit()

    def _set_search_text(self, v: str) -> None:
        if v == self._search_text:
            return
        self._search_text = v
        self.searchTextChanged.emit()

    def _set_selected_task_view_name(self, v: str) -> None:
        if v == self._selected_task_view_name:
            return
        self._selected_task_view_name = v
        self.selectedTaskViewNameChanged.emit()

    def _set_selected_task_id(self, v: str) -> None:
        if v == self._selected_task_id:
            return
        self._selected_task_id = v
        self.selectedTaskIdChanged.emit()
        if self._task_review_active:
            self._collab_ctrl.sync_review_presence(v)

    def _reset_task_lazy_sections(self) -> None:
        self._set_selected_assignment_id("")
        self._set_selected_time_period_start("")
        self._set_selected_time_entry_id("")
        self._set_time_section_loaded_for_task_id("")
        self._set_collaboration_section_loaded_for_task_id("")
        self._assignments_section_loaded_for_task_id = ""
        self._dependencies_section_loaded_for_task_id = ""
        self._skill_requirements_section_loaded_for_task_id = ""
        self._schedule_impact_section_loaded_for_task_id = ""
        self._set_schedule_impact({})

    def _set_schedule_impact(self, v: dict[str, object]) -> None:
        if v == self._schedule_impact:
            return
        self._schedule_impact = v
        self.scheduleImpactChanged.emit()
        self.scheduleImpactSectionLoadedChanged.emit()

    def _set_selected_assignment_id(self, v: str) -> None:
        if v == self._selected_assignment_id:
            return
        self._selected_assignment_id = v
        self.selectedAssignmentIdChanged.emit()

    def _set_selected_time_period_start(self, v: str) -> None:
        if v == self._selected_time_period_start:
            return
        self._selected_time_period_start = v
        self.selectedTimePeriodStartChanged.emit()

    def _set_selected_time_entry_id(self, v: str) -> None:
        if v == self._selected_time_entry_id:
            return
        self._selected_time_entry_id = v
        self.selectedTimeEntryIdChanged.emit()

    def _set_time_section_loaded_for_task_id(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if normalized == self._time_section_loaded_for_task_id:
            return
        self._time_section_loaded_for_task_id = normalized
        self.timeSectionLoadedChanged.emit()

    def _set_collaboration_section_loaded_for_task_id(self, task_id: str) -> None:
        normalized = (task_id or "").strip()
        if normalized == self._collaboration_section_loaded_for_task_id:
            return
        self._collaboration_section_loaded_for_task_id = normalized
        self.collaborationSectionLoadedChanged.emit()

    # ── Saved view helpers ────────────────────────────────────────────

    def _load_saved_task_views(self) -> dict[str, dict[str, object]]:
        raw = self._task_view_store.load_task_saved_views()
        result: dict[str, dict[str, object]] = {}
        for name, state in raw.items():
            normalized = (name or "").strip()
            if normalized and isinstance(state, dict):
                result[normalized] = self._normalize_task_view_state(state)
        return result

    def _persist_saved_task_views(self) -> None:
        self._task_view_store.save_task_saved_views(self._saved_task_views)

    def _refresh_task_view_options(self) -> None:
        options: list[dict[str, str]] = [{"value": "", "label": "Current Filters"}]
        options.extend(
            {"value": name, "label": name} for name in sorted(self._saved_task_views)
        )
        if options == self._task_view_options:
            return
        self._task_view_options = options
        self.taskViewOptionsChanged.emit()
        if self._selected_task_view_name and (
            self._selected_task_view_name not in self._saved_task_views
        ):
            self._set_selected_task_view_name("")

    def _capture_task_view_state(self) -> dict[str, object]:
        return {
            "query": self._search_text,
            "status": self._index_for_option_value(
                self._task_list.statusOptions, self._selected_status_filter
            ),
            "priority": self._index_for_option_value(
                self._task_list.priorityOptions, self._selected_priority_filter
            ),
            "schedule": self._index_for_option_value(
                self._task_list.scheduleOptions, self._selected_schedule_filter
            ),
        }

    def _apply_task_view_state(
        self, state: dict[str, object], *, selected_view_name: str
    ) -> None:
        normalized = self._normalize_task_view_state(state)
        self._set_search_text(str(normalized.get("query", "") or ""))
        self._set_selected_status_filter(
            self._option_value_for_index(
                self._task_list.statusOptions,
                normalized.get("status", 0),
                default_value="all",
            )
        )
        self._set_selected_priority_filter(
            self._option_value_for_index(
                self._task_list.priorityOptions,
                normalized.get("priority", 0),
                default_value="all",
            )
        )
        self._set_selected_schedule_filter(
            self._option_value_for_index(
                self._task_list.scheduleOptions,
                normalized.get("schedule", 0),
                default_value="all",
            )
        )
        self._set_selected_task_view_name(selected_view_name)
        self._task_page = 1
        self.refresh()

    @staticmethod
    def _normalize_task_view_state(state: dict[str, object]) -> dict[str, object]:
        return {
            "query": str(state.get("query", "") or "").strip(),
            "status": ProjectManagementTasksWorkspaceController._coerce_non_negative_int(
                state.get("status", 0)
            ),
            "priority": ProjectManagementTasksWorkspaceController._coerce_non_negative_int(
                state.get("priority", 0)
            ),
            "schedule": ProjectManagementTasksWorkspaceController._coerce_non_negative_int(
                state.get("schedule", 0)
            ),
        }

    @staticmethod
    def _coerce_non_negative_int(value: object) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _index_for_option_value(
        options: list[dict[str, str]], target_value: str
    ) -> int:
        target = str(target_value or "")
        for i, option in enumerate(options):
            if str(option.get("value", "") or "") == target:
                return i
        return 0

    @staticmethod
    def _option_value_for_index(
        options: list[dict[str, str]],
        index_value: object,
        *,
        default_value: str,
    ) -> str:
        idx = ProjectManagementTasksWorkspaceController._coerce_non_negative_int(
            index_value
        )
        if 0 <= idx < len(options):
            return str(options[idx].get("value", "") or default_value)
        if options:
            return str(options[0].get("value", "") or default_value)
        return default_value


__all__ = ["ProjectManagementTasksWorkspaceController"]
