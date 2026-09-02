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
from src.ui_qml.platform.adapters.cycle_count_view_invalidation_adapter import (
    CycleCountViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.document_links_view_invalidation_adapter import (
    DocumentLinksViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.inventory_foundation_view_invalidation_adapter import (
    InventoryFoundationViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.inventory_catalog_view_invalidation_adapter import (
    InventoryCatalogViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.purchase_order_view_invalidation_adapter import (
    PurchaseOrderViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.receipt_view_invalidation_adapter import (
    ReceiptViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.requisition_view_invalidation_adapter import (
    RequisitionViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.reservation_view_invalidation_adapter import (
    ReservationViewInvalidationAdapter,
)
from src.ui_qml.platform.adapters.stock_balance_view_invalidation_adapter import (
    StockBalanceViewInvalidationAdapter,
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
        self._catalog_document_links_view_invalidation_adapter = DocumentLinksViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._catalog_document_links_view_invalidation_adapter.documentLinksStale.connect(
            self._catalog_workspace.on_document_links_stale
        )
        self._catalog_catalog_view_invalidation_adapter = InventoryCatalogViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._catalog_catalog_view_invalidation_adapter.itemListStale.connect(
            self._catalog_workspace.refresh
        )
        self._catalog_catalog_view_invalidation_adapter.itemCategoryListStale.connect(
            self._catalog_workspace.refresh
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
        self._inventory_foundation_view_invalidation_adapter = InventoryFoundationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_foundation_view_invalidation_adapter.storeroomListStale.connect(
            self._inventory_workspace.refresh
        )
        self._inventory_foundation_view_invalidation_adapter.locationListStale.connect(
            self._inventory_workspace.refresh
        )
        self._inventory_foundation_view_invalidation_adapter.reorderPolicyListStale.connect(
            self._inventory_workspace.refresh
        )
        self._inventory_catalog_view_invalidation_adapter = InventoryCatalogViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_catalog_view_invalidation_adapter.itemListStale.connect(
            self._inventory_workspace.refresh_item_options
        )
        self._inventory_balance_view_invalidation_adapter = StockBalanceViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_balance_view_invalidation_adapter.stockBalanceListStale.connect(
            self._inventory_workspace._request_domain_refresh
        )
        self._inventory_balance_view_invalidation_adapter.stockBalanceDetailStale.connect(
            self._inventory_workspace._request_domain_refresh
        )
        self._inventory_cycle_count_view_invalidation_adapter = CycleCountViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_cycle_count_view_invalidation_adapter.cycleCountListStale.connect(
            self._inventory_workspace._request_domain_refresh
        )
        self._inventory_cycle_count_view_invalidation_adapter.cycleCountDetailStale.connect(
            self._inventory_workspace._request_domain_refresh
        )
        self._inventory_receipt_view_invalidation_adapter = ReceiptViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._inventory_receipt_view_invalidation_adapter.receiptListStale.connect(
            self._inventory_workspace._request_domain_refresh
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
        self._reservations_foundation_view_invalidation_adapter = InventoryFoundationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._reservations_foundation_view_invalidation_adapter.storeroomListStale.connect(
            self._reservations_workspace.refresh_storeroom_options
        )
        self._reservations_catalog_view_invalidation_adapter = InventoryCatalogViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._reservations_catalog_view_invalidation_adapter.itemListStale.connect(
            self._reservations_workspace.refresh_item_options
        )
        self._reservations_reservation_view_invalidation_adapter = ReservationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._reservations_reservation_view_invalidation_adapter.reservationListStale.connect(
            self._reservations_workspace._request_domain_refresh
        )
        self._reservations_reservation_view_invalidation_adapter.reservationDetailStale.connect(
            self._reservations_workspace._request_domain_refresh
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
        self._procurement_foundation_view_invalidation_adapter = InventoryFoundationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_foundation_view_invalidation_adapter.storeroomListStale.connect(
            self._procurement_workspace.refresh_site_options
        )
        self._procurement_catalog_view_invalidation_adapter = InventoryCatalogViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_catalog_view_invalidation_adapter.itemListStale.connect(
            self._procurement_workspace.refresh_item_options
        )
        self._procurement_purchase_order_view_invalidation_adapter = PurchaseOrderViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_purchase_order_view_invalidation_adapter.purchaseOrderListStale.connect(
            self._procurement_workspace._request_domain_refresh
        )
        self._procurement_purchase_order_view_invalidation_adapter.purchaseOrderDetailStale.connect(
            self._procurement_workspace._request_domain_refresh
        )
        self._procurement_requisition_view_invalidation_adapter = RequisitionViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_requisition_view_invalidation_adapter.requisitionListStale.connect(
            self._procurement_workspace._request_domain_refresh
        )
        self._procurement_requisition_view_invalidation_adapter.requisitionDetailStale.connect(
            self._procurement_workspace._request_domain_refresh
        )
        self._procurement_receipt_view_invalidation_adapter = ReceiptViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._procurement_receipt_view_invalidation_adapter.receiptListStale.connect(
            self._procurement_workspace._request_domain_refresh
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
        self._pricing_foundation_view_invalidation_adapter = InventoryFoundationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._pricing_foundation_view_invalidation_adapter.storeroomListStale.connect(
            self._pricing_workspace.refresh_site_options
        )
        self._pricing_balance_view_invalidation_adapter = StockBalanceViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._pricing_balance_view_invalidation_adapter.stockBalanceListStale.connect(
            self._pricing_workspace._request_domain_refresh
        )
        self._pricing_balance_view_invalidation_adapter.stockBalanceDetailStale.connect(
            self._pricing_workspace._request_domain_refresh
        )
        self._pricing_receipt_view_invalidation_adapter = ReceiptViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._pricing_receipt_view_invalidation_adapter.receiptListStale.connect(
            self._pricing_workspace._request_domain_refresh
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
        self._dashboard_foundation_view_invalidation_adapter = InventoryFoundationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._dashboard_foundation_view_invalidation_adapter.storeroomListStale.connect(
            self._dashboard_workspace.refresh
        )
        self._dashboard_foundation_view_invalidation_adapter.locationListStale.connect(
            self._dashboard_workspace.refresh
        )
        self._dashboard_catalog_view_invalidation_adapter = InventoryCatalogViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._dashboard_catalog_view_invalidation_adapter.itemListStale.connect(
            self._dashboard_workspace.refresh
        )
        self._dashboard_purchase_order_view_invalidation_adapter = PurchaseOrderViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._dashboard_purchase_order_view_invalidation_adapter.purchaseOrderListStale.connect(
            self._dashboard_workspace.refresh
        )
        self._dashboard_purchase_order_view_invalidation_adapter.purchaseOrderDetailStale.connect(
            self._dashboard_workspace.refresh
        )
        self._dashboard_requisition_view_invalidation_adapter = RequisitionViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._dashboard_requisition_view_invalidation_adapter.requisitionPendingApprovalStale.connect(
            self._dashboard_workspace.refresh
        )
        self._dashboard_reservation_view_invalidation_adapter = ReservationViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )

        self._dashboard_reservation_view_invalidation_adapter.reservationOpenCountStale.connect(
            self._dashboard_workspace._request_domain_refresh
        )
        self._dashboard_balance_view_invalidation_adapter = StockBalanceViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._dashboard_balance_view_invalidation_adapter.stockBalanceListStale.connect(
            self._dashboard_workspace._request_domain_refresh
        )
        self._dashboard_balance_view_invalidation_adapter.stockBalanceDetailStale.connect(
            self._dashboard_workspace._request_domain_refresh
        )
        self._dashboard_receipt_view_invalidation_adapter = ReceiptViewInvalidationAdapter(
            channel=self._view_invalidation_channel,
            tenant_id=self._active_tenant_id() or "",
            organization_id=self._active_organization_id() or "",
            parent=self,
        )
        self._dashboard_receipt_view_invalidation_adapter.receiptListStale.connect(
            self._dashboard_workspace._request_domain_refresh
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
            self._catalog_document_links_view_invalidation_adapter,
            self._inventory_foundation_view_invalidation_adapter,
            self._reservations_foundation_view_invalidation_adapter,
            self._procurement_foundation_view_invalidation_adapter,
            self._pricing_foundation_view_invalidation_adapter,
            self._dashboard_foundation_view_invalidation_adapter,
            self._catalog_catalog_view_invalidation_adapter,
            self._inventory_catalog_view_invalidation_adapter,
            self._reservations_catalog_view_invalidation_adapter,
            self._procurement_catalog_view_invalidation_adapter,
            self._dashboard_catalog_view_invalidation_adapter,
            self._procurement_purchase_order_view_invalidation_adapter,
            self._dashboard_purchase_order_view_invalidation_adapter,
            self._procurement_requisition_view_invalidation_adapter,
            self._dashboard_requisition_view_invalidation_adapter,
        ):
            adapter.set_active_scope(
                tenant_id=tenant_id,
                organization_id=organization_id,
            )


__all__ = ["InventoryProcurementWorkspaceCatalog"]
