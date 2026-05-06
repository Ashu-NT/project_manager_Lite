from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_collaboration_collection_view_model,
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_selector_options,
    serialize_task_catalog_overview_view_model,
    serialize_task_collection_view_model,
    serialize_task_detail_view_model,
    serialize_task_record_view_models,
    serialize_timesheet_collection_view_model,
    serialize_timesheet_detail_view_model,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectTasksWorkspacePresenter,
)


class ProjectManagementTasksWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    projectOptionsChanged = Signal()
    selectedProjectIdChanged = Signal()
    statusOptionsChanged = Signal()
    bulkStatusOptionsChanged = Signal()
    selectedStatusFilterChanged = Signal()
    searchTextChanged = Signal()
    tasksChanged = Signal()
    selectedTaskChanged = Signal()
    selectedTaskIdChanged = Signal()
    selectedTaskIdsChanged = Signal()
    selectedTaskCountChanged = Signal()
    selectedTaskDoneCountChanged = Signal()
    assignmentOptionsChanged = Signal()
    selectedAssignmentIdChanged = Signal()
    dependencyTaskOptionsChanged = Signal()
    dependencyTypeOptionsChanged = Signal()
    assignmentsChanged = Signal()
    dependenciesChanged = Signal()
    timePeriodOptionsChanged = Signal()
    selectedTimePeriodStartChanged = Signal()
    timeAssignmentSummaryChanged = Signal()
    timeEntriesChanged = Signal()
    selectedTimeEntryIdChanged = Signal()
    selectedTimeEntryChanged = Signal()
    collaborationMentionOptionsChanged = Signal()
    collaborationDocumentOptionsChanged = Signal()
    collaborationCommentsChanged = Signal()
    collaborationPresenceChanged = Signal()

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
        self._overview: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "metrics": [],
        }
        self._project_options: list[dict[str, str]] = []
        self._selected_project_id = ""
        self._status_options: list[dict[str, str]] = []
        self._bulk_status_options: list[dict[str, str]] = []
        self._selected_status_filter = "all"
        self._search_text = ""
        self._tasks: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_task: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_task_id = ""
        self._selected_task_ids: list[str] = []
        self._selected_task_count = 0
        self._selected_task_done_count = 0
        self._assignment_options: list[dict[str, str]] = []
        self._selected_assignment_id = ""
        self._dependency_task_options: list[dict[str, str]] = []
        self._dependency_type_options: list[dict[str, str]] = []
        self._assignments: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._dependencies: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._time_period_options: list[dict[str, str]] = []
        self._selected_time_period_start = ""
        self._time_assignment_summary: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._time_entries: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_time_entry_id = ""
        self._selected_time_entry: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._collaboration_mention_options: list[dict[str, str]] = []
        self._collaboration_document_options: list[dict[str, str]] = []
        self._collaboration_comments: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._collaboration_presence: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._bind_domain_events()
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=projectOptionsChanged)
    def projectOptions(self) -> list[dict[str, str]]:
        return self._project_options

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property("QVariantList", notify=bulkStatusOptionsChanged)
    def bulkStatusOptions(self) -> list[dict[str, str]]:
        return self._bulk_status_options

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=tasksChanged)
    def tasks(self) -> dict[str, object]:
        return self._tasks

    @Property("QVariantMap", notify=selectedTaskChanged)
    def selectedTask(self) -> dict[str, object]:
        return self._selected_task

    @Property(str, notify=selectedTaskIdChanged)
    def selectedTaskId(self) -> str:
        return self._selected_task_id

    @Property("QVariantList", notify=selectedTaskIdsChanged)
    def selectedTaskIds(self) -> list[str]:
        return list(self._selected_task_ids)

    @Property(int, notify=selectedTaskCountChanged)
    def selectedTaskCount(self) -> int:
        return self._selected_task_count

    @Property(int, notify=selectedTaskDoneCountChanged)
    def selectedTaskDoneCount(self) -> int:
        return self._selected_task_done_count

    @Property("QVariantList", notify=assignmentOptionsChanged)
    def assignmentOptions(self) -> list[dict[str, str]]:
        return self._assignment_options

    @Property(str, notify=selectedAssignmentIdChanged)
    def selectedAssignmentId(self) -> str:
        return self._selected_assignment_id

    @Property("QVariantList", notify=dependencyTaskOptionsChanged)
    def dependencyTaskOptions(self) -> list[dict[str, str]]:
        return self._dependency_task_options

    @Property("QVariantList", notify=dependencyTypeOptionsChanged)
    def dependencyTypeOptions(self) -> list[dict[str, str]]:
        return self._dependency_type_options

    @Property("QVariantMap", notify=assignmentsChanged)
    def assignments(self) -> dict[str, object]:
        return self._assignments

    @Property("QVariantMap", notify=dependenciesChanged)
    def dependencies(self) -> dict[str, object]:
        return self._dependencies

    @Property("QVariantList", notify=timePeriodOptionsChanged)
    def timePeriodOptions(self) -> list[dict[str, str]]:
        return self._time_period_options

    @Property(str, notify=selectedTimePeriodStartChanged)
    def selectedTimePeriodStart(self) -> str:
        return self._selected_time_period_start

    @Property("QVariantMap", notify=timeAssignmentSummaryChanged)
    def timeAssignmentSummary(self) -> dict[str, object]:
        return self._time_assignment_summary

    @Property("QVariantMap", notify=timeEntriesChanged)
    def timeEntries(self) -> dict[str, object]:
        return self._time_entries

    @Property(str, notify=selectedTimeEntryIdChanged)
    def selectedTimeEntryId(self) -> str:
        return self._selected_time_entry_id

    @Property("QVariantMap", notify=selectedTimeEntryChanged)
    def selectedTimeEntry(self) -> dict[str, object]:
        return self._selected_time_entry

    @Property("QVariantList", notify=collaborationMentionOptionsChanged)
    def collaborationMentionOptions(self) -> list[dict[str, str]]:
        return self._collaboration_mention_options

    @Property("QVariantList", notify=collaborationDocumentOptionsChanged)
    def collaborationDocumentOptions(self) -> list[dict[str, str]]:
        return self._collaboration_document_options

    @Property("QVariantMap", notify=collaborationCommentsChanged)
    def collaborationComments(self) -> dict[str, object]:
        return self._collaboration_comments

    @Property("QVariantMap", notify=collaborationPresenceChanged)
    def collaborationPresence(self) -> dict[str, object]:
        return self._collaboration_presence

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
            workspace_state = self._tasks_workspace_presenter.build_workspace_state(
                project_id=self._selected_project_id or None,
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                selected_task_id=self._selected_task_id or None,
                selected_assignment_id=self._selected_assignment_id or None,
                selected_time_period_start=self._selected_time_period_start,
                selected_time_entry_id=self._selected_time_entry_id or None,
            )
            self._set_overview(
                serialize_task_catalog_overview_view_model(
                    workspace_state.overview
                )
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_bulk_status_options(
                serialize_selector_options(workspace_state.bulk_status_options)
            )
            self._set_selected_status_filter(
                workspace_state.selected_status_filter
            )
            self._set_search_text(workspace_state.search_text)
            self._set_tasks(
                {
                    "title": "Task Catalog",
                    "subtitle": (
                        "Edit delivery tasks, progress, and execution "
                        "priorities."
                    ),
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_task_record_view_models(
                        workspace_state.tasks
                    ),
                }
            )
            self._reconcile_task_bulk_selection(self._tasks["items"])
            self._set_selected_task_id(workspace_state.selected_task_id)
            self._set_selected_task(
                serialize_task_detail_view_model(
                    workspace_state.selected_task_detail
                )
            )
            self._set_assignment_options(
                serialize_selector_options(workspace_state.assignment_options)
            )
            self._set_selected_assignment_id(
                workspace_state.selected_assignment_id
            )
            self._set_dependency_task_options(
                serialize_selector_options(
                    workspace_state.dependency_task_options
                )
            )
            self._set_dependency_type_options(
                serialize_selector_options(
                    workspace_state.dependency_type_options
                )
            )
            self._set_assignments(
                serialize_task_collection_view_model(workspace_state.assignments)
            )
            self._set_dependencies(
                serialize_task_collection_view_model(workspace_state.dependencies)
            )
            self._set_time_period_options(
                serialize_selector_options(workspace_state.time_period_options)
            )
            self._set_selected_time_period_start(
                workspace_state.selected_time_period_start
            )
            self._set_time_assignment_summary(
                serialize_timesheet_detail_view_model(
                    workspace_state.time_assignment_summary
                )
            )
            self._set_time_entries(
                serialize_timesheet_collection_view_model(
                    workspace_state.time_entries
                )
            )
            self._set_selected_time_entry_id(
                workspace_state.selected_time_entry_id
            )
            self._set_selected_time_entry(
                serialize_timesheet_detail_view_model(
                    workspace_state.selected_time_entry_detail
                )
            )
            self._set_collaboration_mention_options(
                serialize_selector_options(
                    workspace_state.collaboration_mention_options
                )
            )
            self._set_collaboration_document_options(
                serialize_selector_options(
                    workspace_state.collaboration_document_options
                )
            )
            self._set_collaboration_comments(
                serialize_collaboration_collection_view_model(
                    workspace_state.collaboration_comments
                )
            )
            self._set_collaboration_presence(
                serialize_collaboration_collection_view_model(
                    workspace_state.collaboration_presence
                )
            )
            self._set_empty_state(workspace_state.empty_state)
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
        self._set_selected_task_id("")
        self._set_selected_assignment_id("")
        self._set_selected_time_period_start("")
        self._set_selected_time_entry_id("")
        self.refresh()

    @Slot(str)
    def setSearchText(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self.refresh()

    @Slot(str)
    def setStatusFilter(self, status_filter: str) -> None:
        normalized_value = (status_filter or "").strip().lower() or "all"
        if normalized_value == self._selected_status_filter.lower():
            return
        self._set_selected_status_filter(normalized_value)
        self.refresh()

    @Slot(str)
    def selectTask(self, task_id: str) -> None:
        normalized_value = (task_id or "").strip()
        if normalized_value == self._selected_task_id:
            return
        self._set_selected_task_id(normalized_value)
        self._set_selected_assignment_id("")
        self._set_selected_time_period_start("")
        self._set_selected_time_entry_id("")
        self.refresh()

    @Slot(str, bool)
    def setTaskBulkSelection(self, task_id: str, selected: bool) -> None:
        normalized_value = (task_id or "").strip()
        if not normalized_value:
            return
        current_ids = list(self._selected_task_ids)
        if selected:
            if normalized_value not in current_ids:
                current_ids.append(normalized_value)
        else:
            current_ids = [
                existing_id for existing_id in current_ids if existing_id != normalized_value
            ]
        self._set_selected_task_ids(current_ids)
        self._sync_selected_task_stats(self._tasks.get("items", []))

    @Slot()
    def selectVisibleTasks(self) -> None:
        visible_task_ids = [
            str(item.get("id", "") or "").strip()
            for item in self._tasks.get("items", [])
            if str(item.get("id", "") or "").strip()
        ]
        self._set_selected_task_ids(visible_task_ids)
        self._sync_selected_task_stats(self._tasks.get("items", []))

    @Slot()
    def clearTaskBulkSelection(self) -> None:
        if not self._selected_task_ids:
            return
        self._set_selected_task_ids([])
        self._sync_selected_task_stats(self._tasks.get("items", []))

    @Slot(str)
    def selectAssignment(self, assignment_id: str) -> None:
        normalized_value = (assignment_id or "").strip()
        if normalized_value == self._selected_assignment_id:
            return
        self._set_selected_assignment_id(normalized_value)
        self._set_selected_time_period_start("")
        self._set_selected_time_entry_id("")
        self.refresh()

    @Slot(str)
    def selectTimePeriod(self, period_start: str) -> None:
        normalized_value = (period_start or "").strip()
        if normalized_value == self._selected_time_period_start:
            return
        self._set_selected_time_period_start(normalized_value)
        self._set_selected_time_entry_id("")
        self.refresh()

    @Slot(str)
    def selectTimeEntry(self, entry_id: str) -> None:
        normalized_value = (entry_id or "").strip()
        if normalized_value == self._selected_time_entry_id:
            return
        self._set_selected_time_entry_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.create_task(
                dict(payload)
            ),
            success_message="Task created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.update_task(
                dict(payload)
            ),
            success_message="Task updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateProgress(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.update_progress(
                dict(payload)
            ),
            success_message="Task progress updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteTask(self, task_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.delete_task(task_id),
            success_message="Task deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createAssignment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.create_assignment(
                dict(payload)
            ),
            success_message="Assignment created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateAssignmentAllocation(
        self,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.update_assignment_allocation(
                dict(payload)
            ),
            success_message="Assignment allocation updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def setAssignmentHours(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.set_assignment_hours(
                dict(payload)
            ),
            success_message="Assignment effort updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def applyBulkStatus(self, payload: dict[str, object]) -> dict[str, object]:
        merged_payload = dict(payload)
        merged_payload.setdefault("taskIds", list(self._selected_task_ids))
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.apply_bulk_status(
                merged_payload
            ),
            success_message="Bulk task status applied.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantList", result="QVariantMap")
    def bulkDeleteTasks(self, task_ids: list[object]) -> dict[str, object]:
        normalized_ids = [
            str(task_id or "").strip()
            for task_id in task_ids
            if str(task_id or "").strip()
        ]
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.bulk_delete_tasks(
                normalized_ids
            ),
            success_message="Selected tasks deleted.",
            on_success=lambda: (
                self.clearTaskBulkSelection(),
                self.refresh(),
            ),
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def addTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.add_task_time_entry(
                dict(payload)
            ),
            success_message="Task time entry added.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTaskTimeEntry(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.update_task_time_entry(
                dict(payload)
            ),
            success_message="Task time entry updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteTaskTimeEntry(self, entry_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.delete_task_time_entry(
                entry_id
            ),
            success_message="Task time entry deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def submitTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.submit_task_period(
                dict(payload)
            ),
            success_message="Task period submitted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def lockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.lock_task_period(
                dict(payload)
            ),
            success_message="Task period locked.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def unlockTaskPeriod(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.unlock_task_period(
                dict(payload)
            ),
            success_message="Task period unlocked.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteAssignment(self, assignment_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.delete_assignment(
                assignment_id
            ),
            success_message="Assignment removed.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDependency(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.create_dependency(
                dict(payload)
            ),
            success_message="Dependency created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteDependency(self, dependency_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.delete_dependency(
                dependency_id
            ),
            success_message="Dependency removed.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def postTaskComment(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.post_task_comment(
                dict(payload)
            ),
            success_message="Task collaboration update posted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def markTaskCollaborationRead(self, task_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.mark_task_collaboration_read(
                task_id
            ),
            success_message="Task collaboration mentions marked as read.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "resource",
            "timesheet_period",
            "task_collaboration",
            scope_code="project_management",
        )

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

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_status_options(self, status_options: list[dict[str, str]]) -> None:
        if status_options == self._status_options:
            return
        self._status_options = status_options
        self.statusOptionsChanged.emit()

    def _set_bulk_status_options(self, bulk_status_options: list[dict[str, str]]) -> None:
        if bulk_status_options == self._bulk_status_options:
            return
        self._bulk_status_options = bulk_status_options
        self.bulkStatusOptionsChanged.emit()

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

    def _set_tasks(self, tasks: dict[str, object]) -> None:
        if tasks == self._tasks:
            return
        self._tasks = tasks
        self.tasksChanged.emit()

    def _set_selected_task(self, selected_task: dict[str, object]) -> None:
        if selected_task == self._selected_task:
            return
        self._selected_task = selected_task
        self.selectedTaskChanged.emit()

    def _set_selected_task_id(self, selected_task_id: str) -> None:
        if selected_task_id == self._selected_task_id:
            return
        self._selected_task_id = selected_task_id
        self.selectedTaskIdChanged.emit()

    def _set_selected_task_ids(self, selected_task_ids: list[str]) -> None:
        normalized_ids = [
            str(task_id or "").strip()
            for task_id in selected_task_ids
            if str(task_id or "").strip()
        ]
        if normalized_ids == self._selected_task_ids:
            return
        self._selected_task_ids = normalized_ids
        self.selectedTaskIdsChanged.emit()

    def _set_selected_task_count(self, selected_task_count: int) -> None:
        if selected_task_count == self._selected_task_count:
            return
        self._selected_task_count = selected_task_count
        self.selectedTaskCountChanged.emit()

    def _set_selected_task_done_count(self, selected_task_done_count: int) -> None:
        if selected_task_done_count == self._selected_task_done_count:
            return
        self._selected_task_done_count = selected_task_done_count
        self.selectedTaskDoneCountChanged.emit()

    def _set_assignment_options(
        self,
        assignment_options: list[dict[str, str]],
    ) -> None:
        if assignment_options == self._assignment_options:
            return
        self._assignment_options = assignment_options
        self.assignmentOptionsChanged.emit()

    def _set_selected_assignment_id(self, selected_assignment_id: str) -> None:
        if selected_assignment_id == self._selected_assignment_id:
            return
        self._selected_assignment_id = selected_assignment_id
        self.selectedAssignmentIdChanged.emit()

    def _set_dependency_task_options(
        self,
        dependency_task_options: list[dict[str, str]],
    ) -> None:
        if dependency_task_options == self._dependency_task_options:
            return
        self._dependency_task_options = dependency_task_options
        self.dependencyTaskOptionsChanged.emit()

    def _set_dependency_type_options(
        self,
        dependency_type_options: list[dict[str, str]],
    ) -> None:
        if dependency_type_options == self._dependency_type_options:
            return
        self._dependency_type_options = dependency_type_options
        self.dependencyTypeOptionsChanged.emit()

    def _set_assignments(self, assignments: dict[str, object]) -> None:
        if assignments == self._assignments:
            return
        self._assignments = assignments
        self.assignmentsChanged.emit()

    def _set_dependencies(self, dependencies: dict[str, object]) -> None:
        if dependencies == self._dependencies:
            return
        self._dependencies = dependencies
        self.dependenciesChanged.emit()

    def _set_time_period_options(
        self,
        time_period_options: list[dict[str, str]],
    ) -> None:
        if time_period_options == self._time_period_options:
            return
        self._time_period_options = time_period_options
        self.timePeriodOptionsChanged.emit()

    def _set_selected_time_period_start(self, selected_time_period_start: str) -> None:
        if selected_time_period_start == self._selected_time_period_start:
            return
        self._selected_time_period_start = selected_time_period_start
        self.selectedTimePeriodStartChanged.emit()

    def _set_time_assignment_summary(self, time_assignment_summary: dict[str, object]) -> None:
        if time_assignment_summary == self._time_assignment_summary:
            return
        self._time_assignment_summary = time_assignment_summary
        self.timeAssignmentSummaryChanged.emit()

    def _set_time_entries(self, time_entries: dict[str, object]) -> None:
        if time_entries == self._time_entries:
            return
        self._time_entries = time_entries
        self.timeEntriesChanged.emit()

    def _set_selected_time_entry_id(self, selected_time_entry_id: str) -> None:
        if selected_time_entry_id == self._selected_time_entry_id:
            return
        self._selected_time_entry_id = selected_time_entry_id
        self.selectedTimeEntryIdChanged.emit()

    def _set_selected_time_entry(self, selected_time_entry: dict[str, object]) -> None:
        if selected_time_entry == self._selected_time_entry:
            return
        self._selected_time_entry = selected_time_entry
        self.selectedTimeEntryChanged.emit()

    def _reconcile_task_bulk_selection(self, task_items: list[dict[str, object]]) -> None:
        visible_task_ids = {
            str(item.get("id", "") or "").strip()
            for item in task_items
            if str(item.get("id", "") or "").strip()
        }
        reconciled_ids = [
            task_id for task_id in self._selected_task_ids if task_id in visible_task_ids
        ]
        self._set_selected_task_ids(reconciled_ids)
        self._sync_selected_task_stats(task_items)

    def _sync_selected_task_stats(self, task_items: list[dict[str, object]]) -> None:
        selected_ids = set(self._selected_task_ids)
        selected_count = len(selected_ids)
        selected_done_count = sum(
            1
            for item in task_items
            if str(item.get("id", "") or "").strip() in selected_ids
            and str(
                (item.get("state", {}) if isinstance(item.get("state"), dict) else {}).get(
                    "status",
                    "",
                )
                or ""
            ).strip().upper()
            == "DONE"
        )
        self._set_selected_task_count(selected_count)
        self._set_selected_task_done_count(selected_done_count)

    def _set_collaboration_mention_options(
        self,
        collaboration_mention_options: list[dict[str, str]],
    ) -> None:
        if collaboration_mention_options == self._collaboration_mention_options:
            return
        self._collaboration_mention_options = collaboration_mention_options
        self.collaborationMentionOptionsChanged.emit()

    def _set_collaboration_document_options(
        self,
        collaboration_document_options: list[dict[str, str]],
    ) -> None:
        if collaboration_document_options == self._collaboration_document_options:
            return
        self._collaboration_document_options = collaboration_document_options
        self.collaborationDocumentOptionsChanged.emit()

    def _set_collaboration_comments(
        self,
        collaboration_comments: dict[str, object],
    ) -> None:
        if collaboration_comments == self._collaboration_comments:
            return
        self._collaboration_comments = collaboration_comments
        self.collaborationCommentsChanged.emit()

    def _set_collaboration_presence(
        self,
        collaboration_presence: dict[str, object],
    ) -> None:
        if collaboration_presence == self._collaboration_presence:
            return
        self._collaboration_presence = collaboration_presence
        self.collaborationPresenceChanged.emit()


__all__ = ["ProjectManagementTasksWorkspaceController"]
