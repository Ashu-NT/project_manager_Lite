from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.modules.inventory_procurement.controllers import (
    InventoryProcurementCatalogWorkspaceController,
    InventoryProcurementDashboardWorkspaceController,
    InventoryProcurementInventoryWorkspaceController,
    InventoryProcurementPricingWorkspaceController,
    InventoryProcurementProcurementWorkspaceController,
    InventoryProcurementReservationsWorkspaceController,
)
from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_workspace_view_model,
)
from src.ui_qml.modules.inventory_procurement.presenters import (
    InventoryCatalogWorkspacePresenter,
    InventoryDashboardWorkspacePresenter,
    InventoryInventoryWorkspacePresenter,
    InventoryPricingWorkspacePresenter,
    InventoryProcurementProcurementWorkspacePresenter,
    InventoryProcurementWorkspacePresenter,
    InventoryReservationsWorkspacePresenter,
    build_inventory_procurement_workspace_presenters,
)

QML_IMPORT_NAME = "InventoryProcurement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("Inventory workspace catalogs are provided by the shell runtime.")
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
        reservations_api = getattr(
            desktop_api_registry,
            "inventory_procurement_reservations",
            None,
        )
        procurement_api = getattr(
            desktop_api_registry,
            "inventory_procurement_procurement",
            None,
        )
        pricing_api = getattr(
            desktop_api_registry,
            "inventory_procurement_pricing",
            None,
        )
        platform_audit = getattr(
            desktop_api_registry,
            "platform_audit",
            None,
        )
        self._catalog_workspace = InventoryProcurementCatalogWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.catalog"
            ),
            catalog_workspace_presenter=InventoryCatalogWorkspacePresenter(
                desktop_api=catalog_api
            ),
            platform_audit=platform_audit,
            parent=self,
        )
        self._inventory_workspace = InventoryProcurementInventoryWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.inventory"
            ),
            inventory_workspace_presenter=InventoryInventoryWorkspacePresenter(
                desktop_api=inventory_api
            ),
            platform_audit=platform_audit,
            parent=self,
        )
        self._reservations_workspace = (
            InventoryProcurementReservationsWorkspaceController(
                workspace_presenter=InventoryProcurementWorkspacePresenter(
                    "inventory_procurement.reservations"
                ),
                reservations_workspace_presenter=InventoryReservationsWorkspacePresenter(
                    desktop_api=reservations_api
                ),
                platform_audit=platform_audit,
                parent=self,
            )
        )
        self._procurement_workspace = (
            InventoryProcurementProcurementWorkspaceController(
                workspace_presenter=InventoryProcurementWorkspacePresenter(
                    "inventory_procurement.procurement"
                ),
                procurement_workspace_presenter=InventoryProcurementProcurementWorkspacePresenter(
                    desktop_api=procurement_api
                ),
                platform_audit=platform_audit,
                parent=self,
            )
        )
        self._pricing_workspace = InventoryProcurementPricingWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.pricing"
            ),
            pricing_workspace_presenter=InventoryPricingWorkspacePresenter(
                desktop_api=pricing_api
            ),
            platform_audit=platform_audit,
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

    @Property(InventoryProcurementReservationsWorkspaceController, constant=True)
    def reservationsWorkspace(self) -> InventoryProcurementReservationsWorkspaceController:
        return self._reservations_workspace

    @Property(InventoryProcurementProcurementWorkspaceController, constant=True)
    def procurementWorkspace(self) -> InventoryProcurementProcurementWorkspaceController:
        return self._procurement_workspace

    @Property(InventoryProcurementPricingWorkspaceController, constant=True)
    def pricingWorkspace(self) -> InventoryProcurementPricingWorkspaceController:
        return self._pricing_workspace

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
