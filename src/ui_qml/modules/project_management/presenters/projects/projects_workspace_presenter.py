from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementProjectsDesktopApi,
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.api.desktop.register import (
    ProjectManagementRegisterDesktopApi,
    build_project_management_register_desktop_api,
)
from src.core.modules.project_management.api.desktop.tasks import (
    ProjectManagementTasksDesktopApi,
    build_project_management_tasks_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
)

from .activity_builder import build_project_activity_state
from .documents_builder import build_project_documents_state
from .financials_builder import build_project_financials_state
from .import_handler import execute_import, preview_import
from .project_command_handler import (
    create_project,
    delete_project,
    set_project_status,
    suggest_code,
    update_project,
)
from .resource_handler import (
    assign_resource_to_project,
    remove_project_resource,
    update_project_resource,
)
from .resources_builder import build_assignable_resource_options, build_project_resources_state
from .risks_builder import build_project_risks_state
from .tasks_builder import build_project_tasks_state
from .workspace_builder import build_project_detail_state, build_workspace_state


class ProjectProjectsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementProjectsDesktopApi | None = None,
        tasks_desktop_api: ProjectManagementTasksDesktopApi | None = None,
        register_desktop_api: ProjectManagementRegisterDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_projects_desktop_api()
        self._tasks_desktop_api = tasks_desktop_api or build_project_management_tasks_desktop_api()
        self._register_desktop_api = register_desktop_api or build_project_management_register_desktop_api()
        self._import_sessions: dict[str, object] = {}

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        status_filter: str = "all",
        selected_project_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ProjectCatalogWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            status_filter=status_filter,
            selected_project_id=selected_project_id,
            page=page,
            page_size=page_size,
        )

    def build_project_detail_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_detail_state(self._desktop_api, project_id=project_id)

    def build_project_tasks_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_tasks_state(self._tasks_desktop_api, project_id=project_id)

    def build_project_resources_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_resources_state(self._desktop_api, project_id=project_id)

    def build_assignable_resource_options(self, *, project_id: str) -> list[dict[str, str]]:
        return build_assignable_resource_options(self._desktop_api, project_id=project_id)

    def assign_resource_to_project(
        self,
        *,
        project_id: str,
        resource_id: str,
        planned_hours: float,
        hourly_rate: float | None,
    ) -> None:
        assign_resource_to_project(
            self._desktop_api,
            project_id=project_id,
            resource_id=resource_id,
            planned_hours=planned_hours,
            hourly_rate=hourly_rate,
        )

    def update_project_resource(
        self,
        *,
        project_resource_id: str,
        planned_hours: float,
        hourly_rate: float | None,
        is_active: bool,
    ) -> None:
        update_project_resource(
            self._desktop_api,
            project_resource_id=project_resource_id,
            planned_hours=planned_hours,
            hourly_rate=hourly_rate,
            is_active=is_active,
        )

    def remove_project_resource(self, *, project_resource_id: str) -> None:
        remove_project_resource(self._desktop_api, project_resource_id=project_resource_id)

    def build_project_financials_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_financials_state(project_id=project_id)

    def build_project_risks_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_risks_state(self._register_desktop_api, project_id=project_id)

    def build_project_documents_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_documents_state(project_id=project_id)

    def build_project_activity_state(self, *, project_id: str) -> ProjectCatalogWorkspaceViewModel:
        return build_project_activity_state(project_id=project_id)

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def create_project(self, payload: dict[str, Any]) -> None:
        create_project(self._desktop_api, payload)

    def update_project(self, payload: dict[str, Any]) -> None:
        update_project(self._desktop_api, payload)

    def set_project_status(self, project_id: str, status: str) -> None:
        set_project_status(self._desktop_api, project_id, status)

    def delete_project(self, project_id: str) -> None:
        delete_project(self._desktop_api, project_id)

    def preview_import(self, *, file_path: str, source_format: str) -> dict[str, object]:
        return preview_import(
            self._import_sessions, file_path=file_path, source_format=source_format
        )

    def execute_import(self, *, session_id: str) -> dict[str, object]:
        return execute_import(self._import_sessions, session_id=session_id)


__all__ = ["ProjectProjectsWorkspacePresenter"]
