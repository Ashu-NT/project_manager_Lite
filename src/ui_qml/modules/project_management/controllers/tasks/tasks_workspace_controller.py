from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
    ProjectManagementWorkspaceControllerBase,
    serialize_workspace_view_model,
)
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
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectTasksWorkspacePresenter,
)

from .task_domain_event_binder import bind_task_domain_events
from .task_export_handler import export_tasks
from .task_facade_signal_binder import bind_task_facade_signals
from .task_lazy_section_loader import (
    load_selected_task_assignments,
    load_selected_task_collaboration,
    load_selected_task_dependencies,
    load_selected_task_schedule_impact,
    load_selected_task_skill_requirements,
    load_selected_task_time,
    load_task_assignments_and_dependencies,
    refresh_time_entries_only,
)
from .task_saved_view_service import TaskSavedViewService
from .task_selection_handler import (
    activate_task,
    on_task_detail_error,
    on_task_detail_loaded,
    reset_task_lazy_sections,
    select_project,
    select_task,
)
from .task_state_setters import TaskStateSettersMixin
from .task_utils import index_for_option_value, normalize_task_view_state, option_value_for_index

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)


@QmlElement
@QmlUncreatable("Project management workspace controllers are provided by the shell runtime.")
class ProjectManagementTasksWorkspaceController(
    TaskStateSettersMixin,
    ProjectManagementWorkspaceControllerBase,
):
    # ── Signals ──────────────────────────────────────────────────────
    taskPageChanged = Signal()
    taskPageSizeChanged = Signal()
    taskTotalCountChanged = Signal()
    tasksTableModelChanged = Signal()
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
    assignmentPreviewChanged = Signal()
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
        # ── Pagination / coordinator state ─────────────────────────────
        self._task_page = 1
        self._task_page_size = 25
        self._task_total_count = 0
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
        self._saved_view_svc = TaskSavedViewService(self._task_view_store)
        self._saved_view_svc.load_and_init()
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
        self._time_ctrl = PMTimeController(**_cb, refresh_time_entries=self._refresh_time_entries_only)
        self._collab_ctrl = PMCollaborationController(**_cb)
        bind_task_facade_signals(
            self,
            self._task_list,
            self._assignments_ctrl,
            self._dependencies_ctrl,
            self._time_ctrl,
            self._collab_ctrl,
        )
        bind_task_domain_events(self)
        self.refresh()

    # ── Sub-controller access properties ─────────────────────────────

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

    # ── Backward-compat properties ────────────────────────────────────

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

    @Property(QObject, constant=True)
    def tasksTableModel(self) -> QObject:
        return self._task_list.tasksTableModel

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

    @Property("QVariantMap", notify=assignmentPreviewChanged)
    def assignmentPreview(self) -> dict[str, object]:
        return self._assignments_ctrl.assignmentPreview

    @Property(QObject, constant=True)
    def assignmentsTableModel(self) -> QObject:
        return self._assignments_ctrl.assignmentsTableModel

    @Property("QVariantMap", notify=dependenciesChanged)
    def dependencies(self) -> dict[str, object]:
        return self._dependencies_ctrl.dependencies

    @Property(QObject, constant=True)
    def dependenciesTableModel(self) -> QObject:
        return self._dependencies_ctrl.dependenciesTableModel

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

    @Property(QObject, constant=True)
    def timeEntriesTableModel(self) -> QObject:
        return self._time_ctrl.timeEntriesTableModel

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

    @Property(int, notify=taskPageChanged)
    def taskPage(self) -> int:
        return self._task_page

    @Property(int, notify=taskPageSizeChanged)
    def taskPageSize(self) -> int:
        return self._task_page_size

    @Property(int, notify=taskTotalCountChanged)
    def taskTotalCount(self) -> int:
        return self._task_total_count

    # ── Refresh ───────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        self._set_is_loading(True)
        try:
            self._set_error_message("")
            self._set_feedback_message("")
            self._set_workspace(
                serialize_workspace_view_model(self._workspace_presenter.build_view_model())
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
        select_project(self, project_id)

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
        select_task(self, task_id)

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
        activate_task(self, task_id)

    def _on_task_detail_loaded(self, data: object) -> None:
        on_task_detail_loaded(self, data)

    def _on_task_detail_error(self, data: object) -> None:
        on_task_detail_error(self, data)

    # ── Lazy section loader slots ─────────────────────────────────────

    @Slot()
    def loadTaskAssignmentsAndDependencies(self) -> None:
        load_task_assignments_and_dependencies(self)

    @Slot()
    def loadSelectedTaskAssignments(self) -> None:
        load_selected_task_assignments(self)

    @Slot()
    def loadSelectedTaskDependencies(self) -> None:
        load_selected_task_dependencies(self)

    @Slot()
    def loadSelectedTaskTime(self) -> None:
        load_selected_task_time(self)

    @Slot()
    def loadSelectedTaskCollaboration(self) -> None:
        load_selected_task_collaboration(self)

    @Slot()
    def loadSelectedTaskSkillRequirements(self) -> None:
        load_selected_task_skill_requirements(self)

    @Slot()
    def loadSelectedTaskScheduleImpact(self) -> None:
        load_selected_task_schedule_impact(self)

    # ── Task review / bulk selection slots ────────────────────────────

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

    # ── Time section selection slots ──────────────────────────────────

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
            load_selected_task_time(self)

    @Slot(str)
    def selectTimePeriod(self, period_start: str) -> None:
        normalized = (period_start or "").strip()
        if normalized == self._selected_time_period_start:
            return
        self._set_selected_time_period_start(normalized)
        self._set_selected_time_entry_id("")
        self._set_time_section_loaded_for_task_id("")
        load_selected_task_time(self)

    @Slot(str)
    def selectTimeEntry(self, entry_id: str) -> None:
        normalized = (entry_id or "").strip()
        if normalized == self._selected_time_entry_id:
            return
        self._set_selected_time_entry_id(normalized)
        self._set_time_section_loaded_for_task_id("")
        load_selected_task_time(self)

    # ── Saved view slots ──────────────────────────────────────────────

    @Slot(str)
    def selectTaskView(self, view_name: str) -> None:
        self._set_selected_task_view_name((view_name or "").strip())

    @Slot(str, result="QVariantMap")
    def saveCurrentTaskView(self, view_name: str) -> dict[str, object]:
        normalized = (view_name or "").strip()
        if not normalized:
            self._set_error_message("Saved view name is required.")
            return {"ok": False, "message": "Saved view name is required."}
        state = {
            "query": self._search_text,
            "status": index_for_option_value(
                self._task_list.statusOptions, self._selected_status_filter
            ),
            "priority": index_for_option_value(
                self._task_list.priorityOptions, self._selected_priority_filter
            ),
            "schedule": index_for_option_value(
                self._task_list.scheduleOptions, self._selected_schedule_filter
            ),
        }
        self._saved_view_svc.save_view(normalized, state)
        self._saved_view_svc.persist()
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
        state = self._saved_view_svc.resolve_view_state(view_name)
        if state is None:
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
        self._saved_view_svc.delete_view(view_name)
        self._saved_view_svc.persist()
        self._refresh_task_view_options()
        self._set_selected_task_view_name("")
        self._set_error_message("")
        self._set_feedback_message(f'Deleted task view "{view_name}".')
        return {"ok": True, "message": f'Deleted task view "{view_name}".'}

    # ── Export slot ───────────────────────────────────────────────────

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTasks(self, columns: list, file_path: str) -> dict[str, object]:
        return export_tasks(self, columns, file_path)

    # ── Mutation delegation slots ─────────────────────────────────────

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return self._task_list.generateEntityCode(entity_type, payload)

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
    def updateAssignmentAllocation(self, payload: dict[str, object]) -> dict[str, object]:
        return self._assignments_ctrl.updateAssignmentAllocation(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def setAssignmentHours(self, payload: dict[str, object]) -> dict[str, object]:
        return self._assignments_ctrl.setAssignmentHours(payload)

    @Slot(str, result="QVariantMap")
    def deleteAssignment(self, assignment_id: str) -> dict[str, object]:
        return self._assignments_ctrl.deleteAssignment(assignment_id)

    @Slot("QVariantMap", result="QVariantMap")
    def validateAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return self._assignments_ctrl.validateAssignment(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return self._dependencies_ctrl.createDependency(payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return self._dependencies_ctrl.updateDependency(payload)

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

    # ── Private helpers ───────────────────────────────────────────────

    def _refresh_time_entries_only(self) -> None:
        refresh_time_entries_only(self)

    def _refresh_task_view_options(self) -> None:
        options = self._saved_view_svc.build_options()
        if options == self._task_view_options:
            return
        self._task_view_options = options
        self.taskViewOptionsChanged.emit()
        if self._selected_task_view_name and not self._saved_view_svc.has_view(
            self._selected_task_view_name
        ):
            self._set_selected_task_view_name("")

    def _apply_task_view_state(
        self, state: dict[str, object], *, selected_view_name: str
    ) -> None:
        normalized = normalize_task_view_state(state)
        self._set_search_text(str(normalized.get("query", "") or ""))
        self._set_selected_status_filter(
            option_value_for_index(
                self._task_list.statusOptions, normalized.get("status", 0), default_value="all"
            )
        )
        self._set_selected_priority_filter(
            option_value_for_index(
                self._task_list.priorityOptions, normalized.get("priority", 0), default_value="all"
            )
        )
        self._set_selected_schedule_filter(
            option_value_for_index(
                self._task_list.scheduleOptions, normalized.get("schedule", 0), default_value="all"
            )
        )
        self._set_selected_task_view_name(selected_view_name)
        self._task_page = 1
        self.refresh()


__all__ = ["ProjectManagementTasksWorkspaceController"]
