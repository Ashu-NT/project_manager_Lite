from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementDashboardDesktopApi,
    build_project_management_dashboard_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardWorkspaceViewModel,
)

from .utils import logger
from .workspace_builder import build_workspace_state


class ProjectDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_dashboard_desktop_api()
        self._build_workspace_state_count = 0

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        baseline_id: str | None = None,
        period_key: str | None = None,
        view_key: str | None = None,
    ) -> ProjectDashboardWorkspaceViewModel:
        self._build_workspace_state_count += 1
        logger.debug(
            "PM dashboard presenter build_workspace_state #%s project=%r baseline=%r period=%r view=%r",
            self._build_workspace_state_count,
            project_id,
            baseline_id,
            period_key,
            view_key,
        )
        return build_workspace_state(
            self._desktop_api,
            project_id=project_id,
            baseline_id=baseline_id,
            period_key=period_key,
            view_key=view_key,
        )


__all__ = ["ProjectDashboardWorkspacePresenter"]
