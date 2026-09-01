from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

from src.ui_qml.platform.adapters.site_view_invalidation_adapter import (
    SiteViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.party_view_invalidation_adapter import (
    PartyViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.document_view_invalidation_adapter import (
    DocumentViewInvalidationAdapter,
)
from src.ui_qml.platform.presenters.tenants.tenant_switcher_presenter import (
    TenantSwitcherPresenter,
)
from src.ui_qml.modules.inventory_procurement.controllers import (
    InventoryProcurementCatalogWorkspaceController,
    InventoryProcurementDashboardWorkspaceController,
    InventoryProcurementInventoryWorkspaceController,
    InventoryProcurementPricingWorkspaceController,
    InventoryProcurementProcurementWorkspaceController,
    InventoryProcurementReservationsWorkspaceController,
)
from src.ui_qml.modules.inventory_procurement.controllers.common import (
    resolve_active_organization_id_from_runtime_api,
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
        self._platform_runtime_api = (
            getattr(desktop_api_registry, "platform_runtime", None)
            if desktop_api_registry is not None else None
        )
        self._view_invalidation_channel = (
            getattr(desktop_api_registry, "platform_view_invalidation_channel", None)
            if desktop_api_registry is not None else None
        )
        self._tenant_switcher_presenter = TenantSwitcherPresenter(
            tenant_api=(
                getattr(desktop_api_registry, "platform_tenant", None)
                if desktop_api_registry is not None else None
            )
        )
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
        platform_activity = getattr(
            desktop_api_registry,
            "platform_activity",
            None,
        )
        self._catalog_workspace = InventoryProcurementCatalogWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.catalog"
            ),
            catalog_workspace_presenter=InventoryCatalogWorkspacePresenter(
                desktop_api=catalog_api
            ),
            activity_api=platform_activity,
            parent=self,
        )
        self._catalog_party_view_invalidation_adapter = PartyViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._catalog_party_view_invalidation_adapter.partyCollectionStale.connect(
            self._catalog_workspace.refresh_party_options
        )
        self._catalog_document_view_invalidation_adapter = DocumentViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._catalog_document_view_invalidation_adapter.documentCollectionStale.connect(
            self._catalog_workspace.refresh_document_options
        )
        self._inventory_workspace = InventoryProcurementInventoryWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.inventory"
            ),
            inventory_workspace_presenter=InventoryInventoryWorkspacePresenter(
                desktop_api=inventory_api
            ),
            activity_api=platform_activity,
            parent=self,
        )
        self._inventory_site_view_invalidation_adapter = SiteViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_site_view_invalidation_adapter.siteCollectionStale.connect(
            self._inventory_workspace.refresh_site_options
        )
        self._inventory_party_view_invalidation_adapter = PartyViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_party_view_invalidation_adapter.partyCollectionStale.connect(
            self._inventory_workspace.refresh_party_options
        )
        self._reservations_workspace = (
            InventoryProcurementReservationsWorkspaceController(
                workspace_presenter=InventoryProcurementWorkspacePresenter(
                    "inventory_procurement.reservations"
                ),
                reservations_workspace_presenter=InventoryReservationsWorkspacePresenter(
                    desktop_api=reservations_api
                ),
                activity_api=platform_activity,
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
                activity_api=platform_activity,
                parent=self,
            )
        )
        self._procurement_site_view_invalidation_adapter = SiteViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_site_view_invalidation_adapter.siteCollectionStale.connect(
            self._procurement_workspace.refresh_site_options
        )
        self._procurement_party_view_invalidation_adapter = PartyViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_party_view_invalidation_adapter.partyCollectionStale.connect(
            self._procurement_workspace.refresh_party_options
        )
        self._pricing_workspace = InventoryProcurementPricingWorkspaceController(
            workspace_presenter=InventoryProcurementWorkspacePresenter(
                "inventory_procurement.pricing"
            ),
            pricing_workspace_presenter=InventoryPricingWorkspacePresenter(
                desktop_api=pricing_api
            ),
            activity_api=platform_activity,
            parent=self,
        )
        self._pricing_site_view_invalidation_adapter = SiteViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._pricing_site_view_invalidation_adapter.siteCollectionStale.connect(
            self._pricing_workspace.refresh_site_options
        )
        self._pricing_party_view_invalidation_adapter = PartyViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._pricing_party_view_invalidation_adapter.partyCollectionStale.connect(
            self._pricing_workspace.refresh_party_options
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

    def _active_tenant_id(self) -> str | None:
        try:
            return self._tenant_switcher_presenter.get_active_tenant_id() or None
        except Exception:
            return None

    def _active_organization_id(self) -> str | None:
        runtime_api = self._platform_runtime_api
        if runtime_api is None:
            return None
        try:
            return resolve_active_organization_id_from_runtime_api(runtime_api)
        except Exception:
            return None

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

    @Slot()
    def refreshAllWorkspaces(self) -> None:
        self.refreshCapabilities()
        for controller in (
            self._catalog_workspace,
            self._inventory_workspace,
            self._reservations_workspace,
            self._procurement_workspace,
            self._pricing_workspace,
            self._dashboard_workspace,
        ):
            refresh = getattr(controller, "refresh", None)
            if callable(refresh):
                refresh()

    @Slot()
    def refreshCapabilities(self) -> None:
        tenant_id = self._active_tenant_id() or ""
        organization_id = self._active_organization_id() or ""
        for adapter in (
            self._inventory_site_view_invalidation_adapter,
            self._pricing_site_view_invalidation_adapter,
            self._procurement_site_view_invalidation_adapter,
            self._catalog_party_view_invalidation_adapter,
            self._inventory_party_view_invalidation_adapter,
            self._pricing_party_view_invalidation_adapter,
            self._procurement_party_view_invalidation_adapter,
            self._catalog_document_view_invalidation_adapter,
        ):
            adapter.set_active_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
            )


__all__ = ["InventoryProcurementWorkspaceCatalog"]
