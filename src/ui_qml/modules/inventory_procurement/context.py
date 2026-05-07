from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot

from src.ui_qml.modules.inventory_procurement.controllers import (
    InventoryProcurementCatalogWorkspaceController,
    InventoryProcurementDashboardWorkspaceController,
    InventoryProcurementInventoryWorkspaceController,
)
from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryDashboardWorkspacePresenter,
    InventoryInventoryWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
    build_inventory_procurement_workspace_presenters,
)


class InventoryProcurementWorkspaceCatalog(QObject):
    def __init__(
        self,
        desktop_api_registry: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._presenters = build_inventory_procurement_workspace_presenters()
        dashboard_api = getattr(
            desktop_api_registry,
            "inventory_procurement_dashboard",
            None,
        )
        catalog_api = getattr(
            desktop_api_registry,
            "inventory_procurement_catalog",
            None,
        )
        inventory_api = getattr(
            desktop_api_registry,
            "inventory_procurement_inventory",
            None,
        )
        self._catalog_workspace = InventoryProcurementCatalogWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.catalog"
            ),
            catalog_workspace_presenter=InventoryCatalogWorkspacePresenter(
                desktop_api=catalog_api
            ),
            parent=self,
        )
        self._inventory_workspace = InventoryProcurementInventoryWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.inventory"
            ),
            inventory_workspace_presenter=InventoryInventoryWorkspacePresenter(
                desktop_api=inventory_api
            ),
            parent=self,
        )
        self._dashboard_workspace = InventoryProcurementDashboardWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.dashboard"
            ),
            dashboard_workspace_presenter=InventoryDashboardWorkspacePresenter(
                desktop_api=dashboard_api
            ),
            parent=self,
        )

    @Property(InventoryProcurementCatalogWorkspaceController, constant=True)
    def catalogWorkspace(self) -> InventoryProcurementCatalogWorkspaceController:
        return self._catalog_workspace

    @Property(InventoryProcurementInventoryWorkspaceController, constant=True)
    def inventoryWorkspace(self) -> InventoryProcurementInventoryWorkspaceController:
        return self._inventory_workspace

    @Property(InventoryProcurementDashboardWorkspaceController, constant=True)
    def dashboardWorkspace(self) -> InventoryProcurementDashboardWorkspaceController:
        return self._dashboard_workspace

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


__all__ = ["InventoryProcurementWorkspaceCatalog"]
