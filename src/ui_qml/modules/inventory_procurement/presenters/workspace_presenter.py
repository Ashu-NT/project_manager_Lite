from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementWorkspaceDesktopApi,
    build_inventory_procurement_workspace_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.routes import (
    build_inventory_procurement_routes,
)
from src.ui_qml.modules.inventory_procurement.view_models.workspace import (
    InventoryProcurementWorkspaceViewModel,
)


class InventoryProcurementWorkspacePresenter:
    def __init__(
        self,
        route_id: str,
        desktop_api: InventoryProcurementWorkspaceDesktopApi | None = None,
    ) -> None:
        self._route_id = route_id
        self._desktop_api = desktop_api or build_inventory_procurement_workspace_desktop_api()

    def build_view_model(self) -> InventoryProcurementWorkspaceViewModel:
        route_by_id = {
            route.route_id: route for route in build_inventory_procurement_routes()
        }
        route = route_by_id[self._route_id]
        descriptor = self._desktop_api.get_workspace(route.route_id)
        summary = descriptor.summary if descriptor is not None else ""
        migration_status = {
            "inventory_procurement.dashboard": "QML dashboard slice active",
            "inventory_procurement.catalog": "QML CRUD catalog slice active",
        }.get(self._route_id, "QML landing zone ready")
        return InventoryProcurementWorkspaceViewModel(
            route_id=route.route_id,
            title=route.title,
            summary=summary,
            migration_status=migration_status,
            legacy_runtime_status="Existing QWidget workspace remains active",
        )


def build_inventory_procurement_workspace_presenters() -> dict[
    str, InventoryProcurementWorkspacePresenter
]:
    desktop_api = build_inventory_procurement_workspace_desktop_api()
    return {
        route.route_id: InventoryProcurementWorkspacePresenter(route.route_id, desktop_api)
        for route in build_inventory_procurement_routes()
    }


__all__ = [
    "InventoryProcurementWorkspacePresenter",
    "build_inventory_procurement_workspace_presenters",
]
