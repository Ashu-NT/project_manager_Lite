from __future__ import annotations

from src.api.desktop.platform import PlatformApprovalDesktopApi
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

    def build_workspace_state(self, *, limit: int = 200) -> CollaborationWorkspaceViewModel:
        return build_workspace_state(self._desktop_api, self._approval_api, limit=limit)

    def mark_task_mentions_read(self, task_id: str) -> None:
        mark_task_mentions_read(self._desktop_api, task_id)

    def approve_request(self, request_id: str, *, note: str | None = None) -> None:
        approve_request(self._approval_api, request_id, note=note)

    def reject_request(self, request_id: str, *, note: str | None = None) -> None:
        reject_request(self._approval_api, request_id, note=note)


__all__ = ["ProjectCollaborationWorkspacePresenter"]
