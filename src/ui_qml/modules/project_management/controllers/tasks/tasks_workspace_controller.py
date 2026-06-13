from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementTaskViewStore,
    ProjectManagementWorkspaceControllerBase,
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

from . import task_bulk_selection_actions as _bulk
from . import task_filter_actions as _filter
from . import task_mutation_facade as _mut
from . import task_pagination_actions as _pag
from . import task_saved_view_actions as _saved_views
from . import task_time_selection_actions as _time_sel
from .task_domain_event_binder import bind_task_domain_events
from .task_export_handler import export_tasks
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
from .task_saved_view_actions import refresh_task_view_options
from .task_saved_view_service import TaskSavedViewService
from .task_selection_handler import (
    activate_task,
    select_project,
    select_task,
)
from .task_state_setters import TaskStateSettersMixin
from .task_subcontroller_factory import create_subcontrollers
from .task_workspace_state_loader import do_refresh

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


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
        refresh_task_view_options(self)
        # ── Sub-controllers ────────────────────────────────────────────
        create_subcontrollers(self)
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
        do_refresh(self)

    # ── Selection / navigation slots ──────────────────────────────────

    @Slot(str)
    def selectProject(self, project_id: str) -> None:
        select_project(self, project_id)

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        _filter.set_search_text(self, search_text)

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        _filter.set_status_filter(self, status_filter)

    @Slot(str)
    def setPriorityFilter(self, priority_filter: str) -> None:
        _filter.set_priority_filter(self, priority_filter)

    @Slot(str)
    def setScheduleFilter(self, schedule_filter: str) -> None:
        _filter.set_schedule_filter(self, schedule_filter)

    @Slot()
    def clearFilters(self) -> None:
        _filter.clear_filters(self)

    @Slot(str)
    def selectTask(self, task_id: str) -> None:
        select_task(self, task_id)

    @Slot(int)
    def setTaskPage(self, page: int) -> None:
        _pag.set_task_page(self, page)

    @Slot(int)
    def setTaskPageSize(self, page_size: int) -> None:
        _pag.set_task_page_size(self, page_size)

    @Slot(str)
    def activateTask(self, task_id: str) -> None:
        activate_task(self, task_id)

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
        _bulk.set_task_review_active(self, active)

    @Slot(str, bool)
    def setTaskBulkSelection(self, task_id: str, selected: bool) -> None:
        _bulk.set_task_bulk_selection(self, task_id, selected)

    @Slot()
    def selectVisibleTasks(self) -> None:
        _bulk.select_visible_tasks(self)

    @Slot()
    def clearTaskBulkSelection(self) -> None:
        _bulk.clear_task_bulk_selection(self)

    # ── Time section selection slots ──────────────────────────────────

    @Slot(str)
    def selectAssignment(self, assignment_id: str) -> None:
        _time_sel.select_assignment(self, assignment_id)

    @Slot(str)
    def selectTimePeriod(self, period_start: str) -> None:
        _time_sel.select_time_period(self, period_start)

    @Slot(str)
    def selectTimeEntry(self, entry_id: str) -> None:
        _time_sel.select_time_entry(self, entry_id)

    # ── Saved view slots ──────────────────────────────────────────────

    @Slot(str)
    def selectTaskView(self, view_name: str) -> None:
        _saved_views.select_task_view(self, view_name)

    @Slot(str, result="QVariantMap")
    def saveCurrentTaskView(self, view_name: str) -> dict[str, object]:
        return _saved_views.save_current_task_view(self, view_name)

    @Slot(result="QVariantMap")
    def applySelectedTaskView(self) -> dict[str, object]:
        return _saved_views.apply_selected_task_view(self)

    @Slot(result="QVariantMap")
    def deleteSelectedTaskView(self) -> dict[str, object]:
        return _saved_views.delete_selected_task_view(self)

    # ── Export slot ───────────────────────────────────────────────────

    @Slot("QVariantList", str, result="QVariantMap")
    def exportTasks(self, columns: list, file_path: str) -> dict[str, object]:
        return export_tasks(self, columns, file_path)

    # ── Mutation delegation slots ─────────────────────────────────────

    @Slot(str, "QVariantMap", result=str)
    def generateEntityCode(self, entity_type: str, payload: dict[str, object]) -> str:
        return _mut.generate_entity_code(self, entity_type, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createTask(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.create_task(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTask(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_task(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateProgress(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_progress(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteTask(self, task_id: str) -> dict[str, object]:
        return _mut.delete_task(self, task_id)

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.apply_bulk_status(self, payload)

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteTasks(self, task_ids: list[object]) -> dict[str, object]:
        return _mut.bulk_delete_tasks(self, task_ids)

    @Slot(result="QVariantMap")
    def undoLastTaskAction(self) -> dict[str, object]:
        return _mut.undo_last_task_action(self)

    @Slot(result="QVariantMap")
    def redoLastTaskAction(self) -> dict[str, object]:
        return _mut.redo_last_task_action(self)

    @Slot("QVariantMap", result="QVariantMap")
    def createAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.create_assignment(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateAssignmentAllocation(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_assignment_allocation(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def setAssignmentHours(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.set_assignment_hours(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteAssignment(self, assignment_id: str) -> dict[str, object]:
        return _mut.delete_assignment(self, assignment_id)

    @Slot("QVariantMap", result="QVariantMap")
    def validateAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.validate_assignment(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.create_dependency(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_dependency(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteDependency(self, dependency_id: str) -> dict[str, object]:
        return _mut.delete_dependency(self, dependency_id)

    @Slot("QVariantMap", result="QVariantMap")
    def addTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.add_task_time_entry(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_task_time_entry(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteTaskTimeEntry(self, entry_id: str) -> dict[str, object]:
        return _mut.delete_task_time_entry(self, entry_id)

    @Slot("QVariantMap", result="QVariantMap")
    def submitTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.submit_task_period(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def lockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.lock_task_period(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def unlockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.unlock_task_period(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def postTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.post_task_comment(self, payload)

    @Slot(str, result="QVariantMap")
    def markTaskCollaborationRead(self, task_id: str) -> dict[str, object]:
        return _mut.mark_task_collaboration_read(self, task_id)

    @Slot(str, str, result="QVariantMap")
    def beginTaskPresence(self, task_id: str, activity: str) -> dict[str, object]:
        return _mut.begin_task_presence(self, task_id, activity)

    @Slot(str, result="QVariantMap")
    def endTaskPresence(self, task_id: str) -> dict[str, object]:
        return _mut.end_task_presence(self, task_id)

    # ── Private helpers ───────────────────────────────────────────────

    def _refresh_time_entries_only(self) -> None:
        refresh_time_entries_only(self)


__all__ = ["ProjectManagementTasksWorkspaceController"]
