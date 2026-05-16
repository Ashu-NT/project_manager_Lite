from __future__ import annotations

from PySide6.QtQml import qmlRegisterModule, qmlRegisterUncreatableType

from src.ui_qml.modules.maintenance.context import MaintenanceWorkspaceCatalog
from src.ui_qml.modules.maintenance.controllers import (
    MaintenanceDashboardWorkspaceController,
    MaintenancePlannerWorkspaceController,
    MaintenanceReliabilityWorkspaceController,
    MaintenanceWorkspaceControllerBase,
)

_REGISTERED = False


def register_maintenance_qml_types() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    qmlRegisterModule("Maintenance.Controllers", 1, 0)
    qmlRegisterUncreatableType(
        MaintenanceWorkspaceControllerBase,
        "Maintenance.Controllers",
        1,
        0,
        "MaintenanceWorkspaceControllerBase",
        "Maintenance workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        MaintenanceDashboardWorkspaceController,
        "Maintenance.Controllers",
        1,
        0,
        "MaintenanceDashboardWorkspaceController",
        "Maintenance workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        MaintenancePlannerWorkspaceController,
        "Maintenance.Controllers",
        1,
        0,
        "MaintenancePlannerWorkspaceController",
        "Maintenance workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        MaintenanceReliabilityWorkspaceController,
        "Maintenance.Controllers",
        1,
        0,
        "MaintenanceReliabilityWorkspaceController",
        "Maintenance workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        MaintenanceWorkspaceCatalog,
        "Maintenance.Controllers",
        1,
        0,
        "MaintenanceWorkspaceCatalog",
        "Maintenance workspace catalogs are provided by the shell runtime.",
    )
    _REGISTERED = True


__all__ = ["register_maintenance_qml_types"]
