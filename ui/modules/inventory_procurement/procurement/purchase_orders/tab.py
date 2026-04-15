from __future__ import annotations

from PySide6.QtWidgets import QWidget

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import (
    InventoryReferenceService,
    InventoryService,
    ItemMasterService,
    ProcurementService,
    PurchasingService,
)
from core.modules.inventory_procurement.domain import PurchaseOrder
from core.platform.auth import UserSessionContext
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.procurement.purchase_orders.actions import PurchaseOrdersActionsMixin
from ui.modules.inventory_procurement.procurement.purchase_orders.surface import PurchaseOrdersSurfaceMixin
from ui.modules.inventory_procurement.procurement.purchase_orders.views import PurchaseOrdersViewMixin
from ui.platform.shared.guards import has_permission


class PurchaseOrdersTab(
    PurchaseOrdersActionsMixin,
    PurchaseOrdersViewMixin,
    PurchaseOrdersSurfaceMixin,
    QWidget,
):
    def __init__(
        self,
        *,
        purchasing_service: PurchasingService,
        procurement_service: ProcurementService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._purchasing_service = purchasing_service
        self._procurement_service = procurement_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[PurchaseOrder] = []
        self._selected_lines = []
        self._site_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._item_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._requisition_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_purchase_orders()
        domain_events.inventory_purchase_orders_changed.connect(self._on_inventory_changed)
        domain_events.inventory_requisitions_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.sites_changed.connect(self._on_inventory_changed)
        domain_events.parties_changed.connect(self._on_inventory_changed)
        domain_events.approvals_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)


__all__ = ["PurchaseOrdersTab"]
