"""Project management QML presenters."""
from src.ui_qml.modules.project_management.presenters.dashboard_presenter import (
    ProjectDashboardPresenter,
)
from src.ui_qml.modules.project_management.presenters.workspace_presenter import (
    ProjectManagementWorkspacePresenter,
    build_project_management_workspace_presenters,
)

__all__ = [
    "ProjectDashboardPresenter",
    "ProjectManagementWorkspacePresenter",
    "build_project_management_workspace_presenters",
]
