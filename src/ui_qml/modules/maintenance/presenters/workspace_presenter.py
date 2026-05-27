from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkspaceDesktopApi,
    build_maintenance_workspace_desktop_api,
)
from src.ui_qml.modules.maintenance.routes import build_maintenance_routes
from src.ui_qml.modules.maintenance.view_models.workspace import (
    MaintenanceWorkspaceViewModel,
)


class MaintenanceWorkspacePresenter:
    def __init__(
        self,
        route_id: str,
        desktop_api: MaintenanceWorkspaceDesktopApi | None = None,
    ) -> None:
        self._route_id = route_id
        self._desktop_api = desktop_api or build_maintenance_workspace_desktop_api()

    def build_view_model(self) -> MaintenanceWorkspaceViewModel:
        route_by_id = {
            route.route_id: route for route in build_maintenance_routes()
        }
        route = route_by_id[self._route_id]
        descriptor = self._desktop_api.get_workspace(route.route_id)
        summary = descriptor.summary if descriptor is not None else ""
        migration_status = {
            "maintenance_management.dashboard": "QML analytics dashboard slice active",
            "maintenance_management.assets": "QML asset-library slice active",
            "maintenance_management.planner": "QML planner review slice active",
            "maintenance_management.preventive": "QML preventive slice active",
            "maintenance_management.reliability": "QML reliability analytics slice active",
            "maintenance_management.work_orders": "QML work-order slice active",
            "maintenance_management.work_requests": "QML work-request slice active",
        }.get(self._route_id, "QML landing zone ready")
        return MaintenanceWorkspaceViewModel(
            route_id=route.route_id,
            title=route.title,
            summary=summary,
            migration_status=migration_status,
            legacy_runtime_status="Existing QWidget workspace remains active",
        )


def build_maintenance_workspace_presenters() -> dict[str, MaintenanceWorkspacePresenter]:
    desktop_api = build_maintenance_workspace_desktop_api()
    return {
        route.route_id: MaintenanceWorkspacePresenter(route.route_id, desktop_api)
        for route in build_maintenance_routes()
    }


__all__ = [
    "MaintenanceWorkspacePresenter",
    "build_maintenance_workspace_presenters",
]
