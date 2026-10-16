from src.core.modules.project_management.api.desktop.dashboard.api import (
    ProjectManagementDashboardDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardWorkspaceViewModel,
)

from .workspace_snapshot_builder import DashboardWorkspaceBuilder


def build_workspace_state(
    desktop_api: ProjectManagementDashboardDesktopApi,
    *,
    project_id: str | None = None,
    baseline_id: str | None = None,
    period_key: str | None = None,
    view_key: str | None = None,
) -> ProjectDashboardWorkspaceViewModel:
    return DashboardWorkspaceBuilder(desktop_api=desktop_api).build_snapshot(
        project_id=project_id, baseline_id=baseline_id, period_key=period_key, view_key=view_key,
    )
