from __future__ import annotations

from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
    build_project_management_collaboration_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationWorkspaceViewModel,
)

from .command_handler import approve_request, mark_task_mentions_read, reject_request
from .workspace_builder import build_workspace_state


class ProjectCollaborationWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementCollaborationDesktopApi | None = None,
        approval_api: PlatformApprovalDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_collaboration_desktop_api()
        self._approval_api = approval_api

    def build_workspace_state(
        self,
        *,
        limit: int = 200,
        selected_project_id: str = "all",
        selected_team_id: str = "all",
        selected_period_key: str = "all",
        selected_unread_key: str = "all",
        mentions_search_text: str = "",
        mentions_page: int = 1,
        mentions_page_size: int = 25,
    ) -> CollaborationWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            self._approval_api,
            limit=limit,
            selected_project_id=selected_project_id,
            selected_team_id=selected_team_id,
            selected_period_key=selected_period_key,
            selected_unread_key=selected_unread_key,
            mentions_search_text=mentions_search_text,
            mentions_page=mentions_page,
            mentions_page_size=mentions_page_size,
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        mark_task_mentions_read(self._desktop_api, task_id)

    def approve_request(self, request_id: str, *, note: str | None = None) -> None:
        approve_request(self._approval_api, request_id, note=note)

    def reject_request(self, request_id: str, *, note: str | None = None) -> None:
        reject_request(self._approval_api, request_id, note=note)


__all__ = ["ProjectCollaborationWorkspacePresenter"]
