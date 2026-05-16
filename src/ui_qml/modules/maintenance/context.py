from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot

from src.ui_qml.modules.maintenance.controllers import (
    MaintenanceAssetsWorkspaceController,
    MaintenanceDashboardWorkspaceController,
    MaintenancePlannerWorkspaceController,
    MaintenanceReliabilityWorkspaceController,
    MaintenanceWorkOrdersWorkspaceController,
    MaintenanceWorkRequestsWorkspaceController,
)
from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_workspace_view_model,
)
from src.ui_qml.modules.maintenance.presenters import (
    MaintenanceAssetsWorkspacePresenter,
    MaintenanceDashboardWorkspacePresenter,
    MaintenancePlannerWorkspacePresenter,
    MaintenanceReliabilityWorkspacePresenter,
    MaintenanceWorkOrdersWorkspacePresenter,
    MaintenanceWorkRequestsWorkspacePresenter,
    MaintenanceWorkspacePresenter,
    build_maintenance_workspace_presenters,
)


class MaintenanceWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api_registry: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenters = build_maintenance_workspace_presenters()
        dashboard_api = getattr(
            desktop_api_registry,
            "maintenance_dashboard",
            None,
        )
        assets_api = getattr(
            desktop_api_registry,
            "maintenance_assets",
            None,
        )
        reliability_api = getattr(
            desktop_api_registry,
            "maintenance_reliability",
            None,
        )
        planner_api = getattr(
            desktop_api_registry,
            "maintenance_planner",
            None,
        )
        work_requests_api = getattr(
            desktop_api_registry,
            "maintenance_work_requests",
            None,
        )
        work_orders_api = getattr(
            desktop_api_registry,
            "maintenance_work_orders",
            None,
        )
        self._dashboard_workspace = MaintenanceDashboardWorkspaceController(
            workspace_presenter=MaintenanceWorkspacePresenter(
                "maintenance_management.dashboard"
            ),
            dashboard_workspace_presenter=MaintenanceDashboardWorkspacePresenter(
                desktop_api=dashboard_api
            ),
            parent=self,
        )
        self._assets_workspace = MaintenanceAssetsWorkspaceController(
            workspace_presenter=MaintenanceWorkspacePresenter(
                "maintenance_management.assets"
            ),
            assets_workspace_presenter=MaintenanceAssetsWorkspacePresenter(
                desktop_api=assets_api
            ),
            parent=self,
        )
        self._planner_workspace = MaintenancePlannerWorkspaceController(
            workspace_presenter=MaintenanceWorkspacePresenter(
                "maintenance_management.planner"
            ),
            planner_workspace_presenter=MaintenancePlannerWorkspacePresenter(
                desktop_api=planner_api
            ),
            parent=self,
        )
        self._work_requests_workspace = MaintenanceWorkRequestsWorkspaceController(
            workspace_presenter=MaintenanceWorkspacePresenter(
                "maintenance_management.work_requests"
            ),
            work_requests_workspace_presenter=MaintenanceWorkRequestsWorkspacePresenter(
                desktop_api=work_requests_api
            ),
            parent=self,
        )
        self._work_orders_workspace = MaintenanceWorkOrdersWorkspaceController(
            workspace_presenter=MaintenanceWorkspacePresenter(
                "maintenance_management.work_orders"
            ),
            work_orders_workspace_presenter=MaintenanceWorkOrdersWorkspacePresenter(
                desktop_api=work_orders_api
            ),
            parent=self,
        )
        self._reliability_workspace = MaintenanceReliabilityWorkspaceController(
            workspace_presenter=MaintenanceWorkspacePresenter(
                "maintenance_management.reliability"
            ),
            reliability_workspace_presenter=MaintenanceReliabilityWorkspacePresenter(
                desktop_api=reliability_api
            ),
            parent=self,
        )

    @Property(MaintenanceDashboardWorkspaceController, constant=True)
    def dashboardWorkspace(self) -> MaintenanceDashboardWorkspaceController:
        return self._dashboard_workspace

    @Property(MaintenanceAssetsWorkspaceController, constant=True)
    def assetsWorkspace(self) -> MaintenanceAssetsWorkspaceController:
        return self._assets_workspace

    @Property(MaintenancePlannerWorkspaceController, constant=True)
    def plannerWorkspace(self) -> MaintenancePlannerWorkspaceController:
        return self._planner_workspace

    @Property(MaintenanceWorkRequestsWorkspaceController, constant=True)
    def workRequestsWorkspace(self) -> MaintenanceWorkRequestsWorkspaceController:
        return self._work_requests_workspace

    @Property(MaintenanceWorkOrdersWorkspaceController, constant=True)
    def workOrdersWorkspace(self) -> MaintenanceWorkOrdersWorkspaceController:
        return self._work_orders_workspace

    @Property(MaintenanceReliabilityWorkspaceController, constant=True)
    def reliabilityWorkspace(self) -> MaintenanceReliabilityWorkspaceController:
        return self._reliability_workspace

    @Slot(str, result="QVariantMap")
    def workspace(self, route_id: str) -> dict[str, object]:
        presenter = self._presenters.get(route_id)
        if presenter is None:
            return {
                "routeId": route_id,
                "title": "",
                "summary": "",
                "migrationStatus": "",
                "legacyRuntimeStatus": "",
            }
        return serialize_workspace_view_model(presenter.build_view_model())


__all__ = ["MaintenanceWorkspaceCatalog"]
