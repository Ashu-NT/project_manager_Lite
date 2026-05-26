from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common import InventoryReferenceService
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryService,
    StockControlService,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_lifecycle import (
    PurchasingLifecycleMixin,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_queries import (
    PurchasingQueryMixin,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_receiving import (
    PurchasingReceivingMixin,
)
from src.core.modules.inventory_procurement.application.procurement.purchasing_support import (
    PurchasingSupportMixin,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StockBalanceRepository,
)
from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
    ReceiptHeaderRepository,
    ReceiptLineRepository,
)
from src.core.platform.approval import ApprovalService
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.documents import Document, DocumentIntegrationService, DocumentLink
from src.core.platform.audit.helpers import record_audit
from src.core.platform.common.exceptions import ValidationError
from src.core.modules.inventory_procurement.application.common.support import normalize_optional_text
from src.core.platform.notifications.domain_events import domain_events


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
        document_integration_service: DocumentIntegrationService | None = None,
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
        self._document_integration_service = document_integration_service

    def list_purchase_order_documents(
        self,
        purchase_order_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Document]:
        if self._document_integration_service is None:
            return []
        po = self.get_purchase_order(purchase_order_id)
        return self._document_integration_service.list_documents_for_entity(
            required_permission="inventory.read",
            operation_label="list purchase order documents",
            module_code="inventory_procurement",
            entity_type="purchase_order",
            entity_id=po.id,
            active_only=active_only,
        )

    def link_document(
        self,
        purchase_order_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> DocumentLink:
        if self._document_integration_service is None:
            raise ValidationError(
                "Document integration is not available.",
                code="DOCUMENT_INTEGRATION_UNAVAILABLE",
            )
        po = self.get_purchase_order(purchase_order_id)
        link = self._document_integration_service.link_existing_document(
            required_permission="inventory.manage",
            operation_label="link purchase order document",
            module_code="inventory_procurement",
            entity_type="purchase_order",
            entity_id=po.id,
            document_id=document_id,
            link_role=link_role,
        )
        record_audit(
            self,
            action="inventory_purchase_order.link_document",
            entity_type="purchase_order",
            entity_id=po.id,
            details={
                "document_id": document_id,
                "link_role": normalize_optional_text(link_role) or "reference",
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(po.id)
        return link

    def unlink_document(
        self,
        purchase_order_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> None:
        if self._document_integration_service is None:
            raise ValidationError(
                "Document integration is not available.",
                code="DOCUMENT_INTEGRATION_UNAVAILABLE",
            )
        po = self.get_purchase_order(purchase_order_id)
        self._document_integration_service.unlink_existing_document(
            required_permission="inventory.manage",
            operation_label="unlink purchase order document",
            module_code="inventory_procurement",
            entity_type="purchase_order",
            entity_id=po.id,
            document_id=document_id,
            link_role=link_role,
        )
        record_audit(
            self,
            action="inventory_purchase_order.unlink_document",
            entity_type="purchase_order",
            entity_id=po.id,
            details={
                "document_id": document_id,
                "link_role": normalize_optional_text(link_role) or "reference",
            },
        )
        domain_events.inventory_purchase_orders_changed.emit(po.id)


__all__ = ["PurchasingService"]
