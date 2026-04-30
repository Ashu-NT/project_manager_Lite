from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
    run_mutation,
    serialize_project_catalog_overview_view_model,
    serialize_project_detail_view_model,
    serialize_project_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    ProjectManagementWorkspacePresenter,
    ProjectProjectsWorkspacePresenter,
)


class ProjectManagementProjectsWorkspaceController(
    ProjectManagementWorkspaceControllerBase
):
    overviewChanged = Signal()
    statusOptionsChanged = Signal()
    selectedStatusFilterChanged = Signal()
    searchTextChanged = Signal()
    projectsChanged = Signal()
    selectedProjectChanged = Signal()
    selectedProjectIdChanged = Signal()

    def __init__(
        self,
        *,
        workspace_presenter: ProjectManagementWorkspacePresenter | None = None,
        projects_workspace_presenter: ProjectProjectsWorkspacePresenter | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace_presenter = workspace_presenter or ProjectManagementWorkspacePresenter(
            "project_management.projects"
        )
        self._projects_workspace_presenter = (
            projects_workspace_presenter or ProjectProjectsWorkspacePresenter()
        )
        self._overview: dict[str, object] = {"title": "", "subtitle": "", "metrics": []}
        self._status_options: list[dict[str, str]] = []
        self._selected_status_filter = "all"
        self._search_text = ""
        self._projects: dict[str, object] = {
            "title": "",
            "subtitle": "",
            "emptyState": "",
            "items": [],
        }
        self._selected_project: dict[str, object] = {
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "",
            "fields": [],
            "state": {},
        }
        self._selected_project_id = ""
        self.refresh()

    @Property("QVariantMap", notify=overviewChanged)
    def overview(self) -> dict[str, object]:
        return self._overview

    @Property("QVariantList", notify=statusOptionsChanged)
    def statusOptions(self) -> list[dict[str, str]]:
        return self._status_options

    @Property(str, notify=selectedStatusFilterChanged)
    def selectedStatusFilter(self) -> str:
        return self._selected_status_filter

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property("QVariantMap", notify=projectsChanged)
    def projects(self) -> dict[str, object]:
        return self._projects

    @Property("QVariantMap", notify=selectedProjectChanged)
    def selectedProject(self) -> dict[str, object]:
        return self._selected_project

    @Property(str, notify=selectedProjectIdChanged)
    def selectedProjectId(self) -> str:
        return self._selected_project_id

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
            workspace_state = self._projects_workspace_presenter.build_workspace_state(
                search_text=self._search_text,
                status_filter=self._selected_status_filter,
                selected_project_id=self._selected_project_id or None,
            )
            self._set_overview(
                serialize_project_catalog_overview_view_model(
                    workspace_state.overview
                )
            )
            self._set_status_options(
                serialize_selector_options(workspace_state.status_options)
            )
            self._set_selected_status_filter(workspace_state.selected_status_filter)
            self._set_search_text(workspace_state.search_text)
            self._set_projects(
                {
                    "title": "Project Catalog",
                    "subtitle": "Create, edit, and review project lifecycle records.",
                    "emptyState": workspace_state.empty_state,
                    "items": serialize_project_record_view_models(
                        workspace_state.projects
                    ),
                }
            )
            self._set_selected_project_id(workspace_state.selected_project_id)
            self._set_selected_project(
                serialize_project_detail_view_model(
                    workspace_state.selected_project_detail
                )
            )
            self._set_empty_state(workspace_state.empty_state)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._set_error_message(str(exc))
        finally:
            self._set_is_loading(False)

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
    def selectProject(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self.refresh()

    @Slot("QVariantMap", result="QVariantMap")
    def createProject(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.create_project(
                dict(payload)
            ),
            success_message="Project created.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot("QVariantMap", result="QVariantMap")
    def updateProject(self, payload: dict[str, object]) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.update_project(
                dict(payload)
            ),
            success_message="Project updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, str, result="QVariantMap")
    def setProjectStatus(
        self,
        project_id: str,
        status: str,
    ) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.set_project_status(
                project_id,
                status,
            ),
            success_message="Project status updated.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    @Slot(str, result="QVariantMap")
    def deleteProject(self, project_id: str) -> dict[str, object]:
        return run_mutation(
            operation=lambda: self._projects_workspace_presenter.delete_project(
                project_id
            ),
            success_message="Project deleted.",
            on_success=self.refresh,
            set_is_busy=self._set_is_busy,
            set_error_message=self._set_error_message,
            set_feedback_message=self._set_feedback_message,
        )

    def _set_overview(self, overview: dict[str, object]) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

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

    def _set_projects(self, projects: dict[str, object]) -> None:
        if projects == self._projects:
            return
        self._projects = projects
        self.projectsChanged.emit()

    def _set_selected_project(self, selected_project: dict[str, object]) -> None:
        if selected_project == self._selected_project:
            return
        self._selected_project = selected_project
        self.selectedProjectChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()


__all__ = ["ProjectManagementProjectsWorkspaceController"]
