from __future__ import annotations

from PySide6.QtQml import qmlRegisterModule, qmlRegisterUncreatableType

from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.modules.project_management.controllers import (
    ProjectManagementDashboardWorkspaceController,
    ProjectManagementFinancialsWorkspaceController,
    ProjectManagementProjectsWorkspaceController,
    ProjectManagementRegisterWorkspaceController,
    ProjectManagementResourcesWorkspaceController,
    ProjectManagementSchedulingWorkspaceController,
    ProjectManagementTasksWorkspaceController,
    ProjectManagementWorkspaceControllerBase,
)

_REGISTERED = False


def register_project_management_qml_types() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    qmlRegisterModule("ProjectManagement.Controllers", 1, 0)
    qmlRegisterUncreatableType(
        ProjectManagementWorkspaceControllerBase,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementWorkspaceControllerBase",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementProjectsWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementProjectsWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementFinancialsWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementFinancialsWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementSchedulingWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementSchedulingWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementTasksWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementTasksWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementResourcesWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementResourcesWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementRegisterWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementRegisterWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementDashboardWorkspaceController,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementDashboardWorkspaceController",
        "Project management workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        ProjectManagementWorkspaceCatalog,
        "ProjectManagement.Controllers",
        1,
        0,
        "ProjectManagementWorkspaceCatalog",
        "Project management workspace catalogs are provided by the shell runtime.",
    )
    _REGISTERED = True


__all__ = ["register_project_management_qml_types"]
