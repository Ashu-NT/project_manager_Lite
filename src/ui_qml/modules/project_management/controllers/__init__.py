from src.ui_qml.modules.project_management.controllers.common import (
    ProjectManagementWorkspaceControllerBase,
)
from src.ui_qml.modules.project_management.controllers.dashboard import (
    ProjectManagementDashboardWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.financials import (
    ProjectManagementFinancialsWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.projects import (
    ProjectManagementProjectsWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.resources import (
    ProjectManagementResourcesWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.scheduling import (
    ProjectManagementSchedulingWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.tasks import (
    ProjectManagementTasksWorkspaceController,
)

__all__ = [
    "ProjectManagementDashboardWorkspaceController",
    "ProjectManagementFinancialsWorkspaceController",
    "ProjectManagementProjectsWorkspaceController",
    "ProjectManagementResourcesWorkspaceController",
    "ProjectManagementSchedulingWorkspaceController",
    "ProjectManagementTasksWorkspaceController",
    "ProjectManagementWorkspaceControllerBase",
]
