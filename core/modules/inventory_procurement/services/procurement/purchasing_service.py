from __future__ import annotations

from sqlalchemy.orm import Session

from core.modules.inventory_procurement.interfaces import (
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
    ReceiptHeaderRepository,
    ReceiptLineRepository,
    StockBalanceRepository,
)
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.procurement.purchasing_lifecycle import PurchasingLifecycleMixin
from core.modules.inventory_procurement.services.procurement.purchasing_queries import PurchasingQueryMixin
from core.modules.inventory_procurement.services.procurement.purchasing_receiving import PurchasingReceivingMixin
from core.modules.inventory_procurement.services.procurement.purchasing_support import PurchasingSupportMixin
from core.modules.inventory_procurement.services.reference_service import InventoryReferenceService
from core.modules.inventory_procurement.services.stock_control import StockControlService
from core.platform.approval import ApprovalService
from core.platform.common.interfaces import OrganizationRepository


class PurchasingService(
    PurchasingSupportMixin,
    PurchasingQueryMixin,
    PurchasingLifecycleMixin,
    PurchasingReceivingMixin,
):
    """Inventory purchasing orchestration composed from focused mixins."""

    def __init__(
        self,
        session: Session,
        purchase_order_repo: PurchaseOrderRepository,
        purchase_order_line_repo: PurchaseOrderLineRepository,
        receipt_header_repo: ReceiptHeaderRepository,
        receipt_line_repo: ReceiptLineRepository,
        *,
        requisition_repo: PurchaseRequisitionRepository,
        requisition_line_repo: PurchaseRequisitionLineRepository,
        balance_repo: StockBalanceRepository,
        organization_repo: OrganizationRepository,
        reference_service: InventoryReferenceService,
        inventory_service: InventoryService,
        item_service: ItemMasterService,
        stock_service: StockControlService,
        approval_service: ApprovalService,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._purchase_order_repo = purchase_order_repo
        self._purchase_order_line_repo = purchase_order_line_repo
        self._receipt_header_repo = receipt_header_repo
        self._receipt_line_repo = receipt_line_repo
        self._requisition_repo = requisition_repo
        self._requisition_line_repo = requisition_line_repo
        self._balance_repo = balance_repo
        self._organization_repo = organization_repo
        self._reference_service = reference_service
        self._inventory_service = inventory_service
        self._item_service = item_service
        self._stock_service = stock_service
        self._approval_service = approval_service
        self._user_session = user_session
        self._audit_service = audit_service


__all__ = ["PurchasingService"]
