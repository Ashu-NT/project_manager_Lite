from __future__ import annotations

from PySide6.QtWidgets import QWidget

from application.platform import PlatformRuntimeApplicationService
from core.modules.inventory_procurement import (
    InventoryReferenceService,
    InventoryService,
    ItemMasterService,
    ProcurementService,
)
from core.modules.inventory_procurement.domain import PurchaseRequisition
from core.platform.auth import UserSessionContext
from core.platform.notifications.domain_events import domain_events
from ui.modules.inventory_procurement.procurement.requisitions.actions import RequisitionsActionsMixin
from ui.modules.inventory_procurement.procurement.requisitions.surface import RequisitionsSurfaceMixin
from ui.modules.inventory_procurement.procurement.requisitions.views import RequisitionsViewMixin
from ui.platform.shared.guards import has_permission


class RequisitionsTab(
    RequisitionsActionsMixin,
    RequisitionsViewMixin,
    RequisitionsSurfaceMixin,
    QWidget,
):
    def __init__(
        self,
        *,
        procurement_service: ProcurementService,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        reference_service: InventoryReferenceService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._procurement_service = procurement_service
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._reference_service = reference_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(self._user_session, "inventory.manage")
        self._rows: list[PurchaseRequisition] = []
        self._selected_lines = []
        self._site_lookup: dict[str, object] = {}
        self._storeroom_lookup: dict[str, object] = {}
        self._item_lookup: dict[str, object] = {}
        self._party_lookup: dict[str, object] = {}
        self._setup_ui()
        self.reload_requisitions()
        domain_events.inventory_requisitions_changed.connect(self._on_inventory_changed)
        domain_events.inventory_items_changed.connect(self._on_inventory_changed)
        domain_events.inventory_storerooms_changed.connect(self._on_inventory_changed)
        domain_events.sites_changed.connect(self._on_inventory_changed)
        domain_events.parties_changed.connect(self._on_inventory_changed)
        domain_events.approvals_changed.connect(self._on_inventory_changed)
        domain_events.organizations_changed.connect(self._on_inventory_changed)


__all__ = ["RequisitionsTab"]
