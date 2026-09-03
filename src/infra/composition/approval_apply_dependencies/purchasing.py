from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.procurement.purchasing_service import (
    PurchasingService,
)
from src.core.modules.inventory_procurement.infrastructure.approval.purchasing_apply_participant import (
    PurchasingApprovalDeps,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.catalog import (
    SqlAlchemyStockItemRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.inventory import (
    SqlAlchemyStockBalanceRepository,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseOrderLineRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
    SqlAlchemyReceiptHeaderRepository,
    SqlAlchemyReceiptLineRepository,
)


def build_purchasing_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    organization_repo=None,
) -> PurchasingApprovalDeps:
 
    purchase_order_repo = SqlAlchemyPurchaseOrderRepository(
        session, tenant_context_service=tenant_context_service
    )
    purchase_order_line_repo = SqlAlchemyPurchaseOrderLineRepository(
        session, tenant_context_service=tenant_context_service
    )
    receipt_header_repo = SqlAlchemyReceiptHeaderRepository(
        session, tenant_context_service=tenant_context_service
    )
    receipt_line_repo = SqlAlchemyReceiptLineRepository(
        session, tenant_context_service=tenant_context_service
    )
    requisition_repo = SqlAlchemyPurchaseRequisitionRepository(
        session, tenant_context_service=tenant_context_service
    )
    requisition_line_repo = SqlAlchemyPurchaseRequisitionLineRepository(
        session, tenant_context_service=tenant_context_service
    )
    balance_repo = SqlAlchemyStockBalanceRepository(
        session, tenant_context_service=tenant_context_service
    )
    item_repo = SqlAlchemyStockItemRepository(
        session, tenant_context_service=tenant_context_service
    )
    item_service = ItemMasterService(
        session,
        item_repo,
        organization_repo=organization_repo,
        party_service=None,
        document_integration_service=None,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    purchasing_service = PurchasingService(
        session,
        purchase_order_repo,
        purchase_order_line_repo,
        receipt_header_repo,
        receipt_line_repo,
        requisition_repo=requisition_repo,
        requisition_line_repo=requisition_line_repo,
        balance_repo=balance_repo,
        organization_repo=organization_repo,
        reference_service=None,
        inventory_service=None,
        item_service=item_service,
        stock_service=None,
        approval_service=None,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        document_integration_service=None,
        procurement_financial_outbox_service=None,
    )
    return PurchasingApprovalDeps(purchasing_service=purchasing_service)


__all__ = ["build_purchasing_approval_deps"]
