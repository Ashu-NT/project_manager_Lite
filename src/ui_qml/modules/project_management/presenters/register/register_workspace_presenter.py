from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementRegisterDesktopApi,
    build_project_management_register_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterWorkspaceViewModel,
)

from .command_handler import create_entry, delete_entry, suggest_code, update_entry
from .utils import WorkspaceMode
from .workspace_builder import build_workspace_state


class ProjectRegisterWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementRegisterDesktopApi | None = None,
        workspace_mode: WorkspaceMode = "register",
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_register_desktop_api()
        self._workspace_mode = workspace_mode

    def build_workspace_state(
        self,
        *,
        project_id: str = "all",
        type_filter: str = "all",
        status_filter: str = "all",
        severity_filter: str = "all",
        search_text: str = "",
        selected_entry_id: str | None = None,
    ) -> RegisterWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            project_id=project_id,
            type_filter=type_filter,
            status_filter=status_filter,
            severity_filter=severity_filter,
            search_text=search_text,
            selected_entry_id=selected_entry_id,
            workspace_mode=self._workspace_mode,
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def create_entry(self, payload: dict[str, Any]) -> None:
        create_entry(self._desktop_api, payload, workspace_mode=self._workspace_mode)

    def update_entry(self, payload: dict[str, Any]) -> None:
        update_entry(self._desktop_api, payload, workspace_mode=self._workspace_mode)

    def delete_entry(self, entry_id: str) -> None:
        delete_entry(self._desktop_api, entry_id)


__all__ = ["ProjectRegisterWorkspacePresenter"]
