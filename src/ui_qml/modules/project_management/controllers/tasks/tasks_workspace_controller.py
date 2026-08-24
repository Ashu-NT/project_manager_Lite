from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    serialize_task_collection_view_model,
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
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

from . import task_bulk_selection_actions as _bulk
from . import task_filter_actions as _filter
from . import task_mutation_facade as _mut
from . import task_pagination_actions as _pag
from . import task_time_selection_actions as _time_sel
from .task_domain_event_binder import bind_task_domain_events
from .task_export_handler import export_tasks
from .task_lazy_section_loader import (
    load_selected_task_activity,
    update_task_activity_query,
    load_selected_task_assignments,
    load_selected_task_collaboration,
    load_selected_task_dependencies,
    load_selected_task_schedule_impact,
    load_selected_task_skill_requirements,
    load_selected_task_time,
    load_task_assignments_and_dependencies,
    refresh_time_entries_only,
)
from .task_selection_handler import (
    activate_task,
    select_project,
    select_task,
)
from .task_state_setters import TaskStateSettersMixin
from .task_subcontroller_factory import create_subcontrollers
from .task_workspace_state_loader import do_refresh

logger = logging.getLogger(__name__)

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
    taskSortKeyChanged = Signal()
    taskSortDirectionChanged = Signal()
    tasksTableModelChanged = Signal()
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    statusOptionsChanged = Signal()
    bulkStatusOptionsChanged = Signal()
    priorityOptionsChanged = Signal()
    scheduleOptionsChanged = Signal()
    constraintOptionsChanged = Signal()
    selectedStatusFilterChanged = Signal()
    selectedPriorityFilterChanged = Signal()
    selectedScheduleFilterChanged = Signal()
    milestonesOnlyFilterChanged = Signal()
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
    timeResourceFilterChanged = Signal()
    timePageChanged = Signal()
    taskTimeSummaryChanged = Signal()
    taskTimeEntriesPageChanged = Signal()
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
    scheduleImpactPreviewChanged = Signal()
    taskActivityChanged = Signal()
    taskActivitySectionLoadedChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        tasks_workspace_presenter: ProjectTasksWorkspacePresenter | None = None,
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
        self._task_sort_key = "wbsCode"
        self._task_sort_direction = 0
        self._selected_project_id = ""
        self._selected_status_filter = "all"
        self._selected_priority_filter = "all"
        self._selected_schedule_filter = "all"
        self._milestones_only_filter = False
        self._search_text = ""
        self._selected_task_id = ""
        self._selected_assignment_id = ""
        self._time_resource_filter = ""
        self._time_page = 1
        self._selected_time_entry_id = ""
        self._task_review_active = False
        self._time_section_loaded_for_task_id = ""
        self._collaboration_section_loaded_for_task_id = ""
        self._assignments_section_loaded_for_task_id = ""
        self._dependencies_section_loaded_for_task_id = ""
        self._skill_requirements_section_loaded_for_task_id = ""
        self._schedule_impact_section_loaded_for_task_id = ""
        self._schedule_impact: dict[str, object] = {}
        self._schedule_impact_preview: dict[str, object] = {}
        self._task_activity_section_loaded_for_task_id = ""
        self._task_activity: dict[str, object] = {
            "title": "Activity", "subtitle": "", "emptyState": "Open this section to load task activity.",
            "items": [], "searchText": "", "category": "all", "page": 1,
            "pageSize": 25, "total": 0, "sortKey": "occurredAt", "sortDirection": "desc",
        }
        self._task_activity_table_model = DynamicTableModel(self)
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

    @Property("QVariantList", notify=constraintOptionsChanged)
    def constraintOptions(self) -> list[dict[str, object]]:
        # Static (never changes at runtime for a given session) -- a
        # real notify signal is declared only because QML properties
        # need one for binding correctness; nothing ever emits it.
        return list(self._tasks_workspace_presenter.list_constraint_options())

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=selectedPriorityFilterChanged)
    def selectedPriorityFilter(self) -> str:
        return self._selected_priority_filter

    @Property(str, notify=selectedScheduleFilterChanged)
    def selectedScheduleFilter(self) -> str:
        return self._selected_schedule_filter

    @Property(bool, notify=milestonesOnlyFilterChanged)
    def milestonesOnlyFilter(self) -> bool:
        return self._milestones_only_filter

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

    @Property("QVariantList", notify=tasksChanged)
    def wbsParentOptions(self) -> list[dict[str, str]]:
        return self._task_list.wbsParentOptions

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

    @Property(str, notify=timeResourceFilterChanged)
    def timeResourceFilter(self) -> str:
        return self._time_resource_filter

    @Property(int, notify=timePageChanged)
    def timePage(self) -> int:
        return self._time_page

    @Property("QVariantMap", notify=taskTimeSummaryChanged)
    def taskTimeSummary(self) -> dict[str, object]:
        return self._time_ctrl.taskTimeSummary

    @Property("QVariantMap", notify=taskTimeEntriesPageChanged)
    def taskTimeEntriesPage(self) -> dict[str, object]:
        return self._time_ctrl.taskTimeEntriesPage

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

    @Property("QVariantMap", notify=scheduleImpactPreviewChanged)
    def scheduleImpactPreview(self) -> dict[str, object]:
        return self._schedule_impact_preview

    @Property(bool, notify=scheduleImpactSectionLoadedChanged)
    def isScheduleImpactSectionLoaded(self) -> bool:
        return (
            bool(self._selected_task_id)
            and self._schedule_impact_section_loaded_for_task_id == self._selected_task_id
        )

    @Property("QVariantMap", notify=taskActivityChanged)
    def taskActivity(self) -> dict[str, object]:
        return self._task_activity

    @Property(QObject, constant=True)
    def taskActivityTableModel(self) -> QObject:
        return self._task_activity_table_model

    @Property(bool, notify=taskActivitySectionLoadedChanged)
    def isTaskActivitySectionLoaded(self) -> bool:
        return (
            bool(self._selected_task_id)
            and self._task_activity_section_loaded_for_task_id == self._selected_task_id
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

    @Property(str, notify=taskSortKeyChanged)
    def taskSortKey(self) -> str:
        return self._task_sort_key

    @Property(int, notify=taskSortDirectionChanged)
    def taskSortDirection(self) -> int:
        return self._task_sort_direction

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

    @Slot(bool)
    def setMilestonesOnlyFilter(self, milestones_only: bool) -> None:
        _filter.set_milestones_only_filter(self, milestones_only)

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

    @Slot(str, int)
    def setTaskSort(self, sort_key: str, sort_direction: int) -> None:
        _pag.set_task_sort(self, sort_key, sort_direction)

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

    @Slot(int, result="QVariantMap")
    def previewTaskScheduleImpact(self, delay_working_days: int) -> dict[str, object]:
        """Explicit "Preview Impact" what-if (§12/§13) -- never run
        automatically. A genuine simulation (two CPM passes), so this is
        deliberately a separate action from loadSelectedTaskScheduleImpact's
        cheap current-facts auto-load (§26)."""
        try:
            preview = self._tasks_workspace_presenter.build_task_schedule_impact_preview_state(
                task_id=self._selected_task_id,
                project_id=self._selected_project_id or None,
                delay_working_days=delay_working_days,
            )
        except Exception as exc:
            logger.exception(
                "previewTaskScheduleImpact failed task_id=%s project_id=%s delay_working_days=%s",
                self._selected_task_id,
                self._selected_project_id,
                delay_working_days,
            )
            self._set_section_error("scheduleImpact", str(exc))
            preview = {}
        else:
            logger.debug(
                "previewTaskScheduleImpact result task_id=%s delay_working_days=%s isAvailable=%s affectedCount=%s",
                self._selected_task_id,
                delay_working_days,
                preview.get("isAvailable"),
                preview.get("affectedCount"),
            )
        self._set_schedule_impact_preview(preview)
        return preview

    @Slot()
    def clearScheduleImpactPreview(self) -> None:
        self._set_schedule_impact_preview({})

    @Slot()
    def loadSelectedTaskActivity(self) -> None:
        load_selected_task_activity(self)

    @Slot(str)
    def setTaskAssignmentsSearch(self, value: str) -> None: self._assignments_ctrl.setSearch(value)

    @Slot(str)
    def setTaskAssignmentsResponse(self, value: str) -> None: self._assignments_ctrl.setResponseStatus(value)

    @Slot(int)
    def setTaskAssignmentsPage(self, value: int) -> None: self._assignments_ctrl.setPage(value)

    @Slot(int)
    def setTaskAssignmentsPageSize(self, value: int) -> None: self._assignments_ctrl.setPageSize(value)

    @Slot(str, int)
    def setTaskAssignmentsSort(self, key: str, direction: int) -> None: self._assignments_ctrl.setSort(key, direction)

    @Slot(str)
    def setTaskDependenciesSearch(self, value: str) -> None: self._dependencies_ctrl.setSearch(value)

    @Slot(str, str)
    def setTaskDependenciesFilters(self, direction: str, dependency_type: str) -> None:
        self._dependencies_ctrl.setFilters(direction, dependency_type)

    @Slot(int)
    def setTaskDependenciesPage(self, value: int) -> None: self._dependencies_ctrl.setPage(value)

    @Slot(int)
    def setTaskDependenciesPageSize(self, value: int) -> None: self._dependencies_ctrl.setPageSize(value)

    @Slot(str, int)
    def setTaskDependenciesSort(self, key: str, direction: int) -> None: self._dependencies_ctrl.setSort(key, direction)

    @Slot(str)
    def setTaskActivitySearch(self, value: str) -> None:
        update_task_activity_query(self, searchText=str(value or "").strip())

    @Slot(str)
    def setTaskActivityCategory(self, value: str) -> None:
        update_task_activity_query(self, category=value)

    @Slot(int)
    def setTaskActivityPage(self, value: int) -> None:
        update_task_activity_query(self, page=max(1, value))

    @Slot(int)
    def setTaskActivityPageSize(self, value: int) -> None:
        update_task_activity_query(self, pageSize=max(1, value), page=1)

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
    def filterTaskTimeEntriesByResource(self, resource_id: str) -> None:
        _time_sel.filter_task_time_entries_by_resource(self, resource_id)

    @Slot(int)
    def setTaskTimeEntriesPage(self, page: int) -> None:
        _time_sel.set_task_time_entries_page(self, page)

    @Slot(str)
    def selectTimeEntry(self, entry_id: str) -> None:
        _time_sel.select_time_entry(self, entry_id)

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
    def updateSchedulingConstraint(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_task_scheduling_constraint(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def moveTaskInWbs(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.move_task_in_wbs(self, payload)

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
    def updateAssignmentPlannedHours(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.update_assignment_planned_hours(self, payload)

    @Slot(str, result="QVariantMap")
    def deleteAssignment(self, assignment_id: str) -> dict[str, object]:
        return _mut.delete_assignment(self, assignment_id)

    @Slot(str, result="QVariantMap")
    def acceptAssignment(self, assignment_id: str) -> dict[str, object]:
        return _mut.accept_assignment(self, assignment_id)

    @Slot("QVariantMap", result="QVariantMap")
    def declineAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.decline_assignment(self, payload)

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
    def postTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.post_task_comment(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def editTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.edit_task_comment(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def deleteTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.delete_task_comment(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def reactToTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return _mut.react_to_task_comment(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def removeTaskCommentReaction(
        self,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return _mut.remove_task_comment_reaction(self, payload)

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

    def _refresh_time_entries_after_mutation(self) -> None:
        # Successful create/update/delete returns Time to capture mode. The
        # mutation refresh must not preserve an edit selection or select a row
        # implicitly; failed mutations never call this and keep the draft.
        self._set_selected_time_entry_id("")
        refresh_time_entries_only(self)


__all__ = ["ProjectManagementTasksWorkspaceController"]
