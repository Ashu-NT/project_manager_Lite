"""Maintenance QML presenters."""

from src.ui_qml.modules.maintenance.presenters.assets import (
    MaintenanceAssetsWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.dashboard_workspace_presenter import (
    MaintenanceDashboardWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.planner_workspace_presenter import (
    MaintenancePlannerWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.preventive import (
    MaintenancePreventiveWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.reliability_workspace_presenter import (
    MaintenanceReliabilityWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.work_orders_workspace_presenter import (
    MaintenanceWorkOrdersWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.work_requests_workspace_presenter import (
    MaintenanceWorkRequestsWorkspacePresenter,
)
from src.ui_qml.modules.maintenance.presenters.workspace_presenter import (
    MaintenanceWorkspacePresenter,
    build_maintenance_workspace_presenters,
)

__all__ = [
    "MaintenanceAssetsWorkspacePresenter",
    "MaintenanceDashboardWorkspacePresenter",
    "MaintenancePlannerWorkspacePresenter",
    "MaintenancePreventiveWorkspacePresenter",
    "MaintenanceReliabilityWorkspacePresenter",
    "MaintenanceWorkOrdersWorkspacePresenter",
    "MaintenanceWorkRequestsWorkspacePresenter",
    "MaintenanceWorkspacePresenter",
    "build_maintenance_workspace_presenters",
]
