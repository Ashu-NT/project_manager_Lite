"""Project management QML presenters."""
from src.ui_qml.modules.project_management.presenters.dashboard_presenter import (
    ProjectDashboardPresenter,
)
from src.ui_qml.modules.project_management.presenters.dashboard_workspace_presenter import (
    ProjectDashboardWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.financials_workspace_presenter import (
    ProjectFinancialsWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.projects_workspace_presenter import (
    ProjectProjectsWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.resources_workspace_presenter import (
    ProjectResourcesWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.scheduling_workspace_presenter import (
    ProjectSchedulingWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.tasks_workspace_presenter import (
    ProjectTasksWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.workspace_presenter import (
    ProjectManagementWorkspacePresenter,
    build_project_management_workspace_presenters,
)

__all__ = [
    "ProjectDashboardPresenter",
    "ProjectDashboardWorkspacePresenter",
    "ProjectFinancialsWorkspacePresenter",
    "ProjectManagementWorkspacePresenter",
    "ProjectProjectsWorkspacePresenter",
    "ProjectResourcesWorkspacePresenter",
    "ProjectSchedulingWorkspacePresenter",
    "ProjectTasksWorkspacePresenter",
    "build_project_management_workspace_presenters",
]
