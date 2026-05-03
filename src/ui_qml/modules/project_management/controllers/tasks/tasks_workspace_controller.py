from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_selector_options,
    serialize_task_catalog_overview_view_model,
    serialize_task_detail_view_model,
    serialize_task_record_view_models,
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
    selectedStatusFilterChanged = Signal()
    searchTextChanged = Signal()
    tasksChanged = Signal()
    selectedTaskChanged = Signal()
    selectedTaskIdChanged = Signal()

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
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._project_options: list[dict[str, str]] = []
        self._selected_project_id = ""
        self._status_options: list[dict[str, str]] = []
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
            )
            self._set_overview(
                serialize_task_catalog_overview_view_model(workspace_state.overview)
            )
            self._set_project_options(
                serialize_selector_options(workspace_state.project_options)
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_selected_status_filter(workspace_state.selected_status_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_tasks(
                {
                    "title": "Task Catalog",
                    "subtitle": "Edit delivery tasks, progress, and execution priorities.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_task_record_view_models(workspace_state.tasks),
                }
            )
            self._set_selected_task_id(workspace_state.selected_task_id)
            self._set_selected_task(
                serialize_task_detail_view_model(workspace_state.selected_task_detail)
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
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.create_task(dict(payload)),
            success_message="Task created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateTask(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.update_task(dict(payload)),
            success_message="Task updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateProgress(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._tasks_workspace_presenter.update_progress(dict(payload)),
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

    def _bind_domain_events(self) -> None:
        self._subscribe_domain_change(
            "project",
            "project_tasks",
            "resource",
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


__all__ = ["ProjectManagementTasksWorkspaceController"]
