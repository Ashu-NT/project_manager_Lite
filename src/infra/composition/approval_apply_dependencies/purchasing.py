"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for
`purchase_order.submit` (Purchasing family).

This is a plain function -- never a generic, type-keyed registry -- called explicitly at its own
`register_apply_handler` call site.
"""

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
    """Every transaction-sensitive collaborator (every repository, `ItemMasterService`, and
    `PurchasingService` itself) is constructed fresh, bound to `session` -- never the caller's
    own, possibly different, Session. Unlike PM/Platform, Inventory does not build its
    repositories via `build_repository_bundle(session)` -- `inventory_registry.py` constructs
    each `SqlAlchemy*Repository` directly, inline, so this factory does the same, parameterized by
    the supplied `session`/`tenant_context_service` instead of a hardcoded
    `platform_services.session`.

    `user_session`/`tenant_context_service` are ambient, stateless-with-respect-to-this-transaction
    collaborators, passed through as-is (ADR-005 Section 24, Round 7's "ambient collaborators ...
    may be reused as-is" rule). `organization_repo` is accepted the same way, defaulting to
    `None`, for structural consistency with the other approval-apply factories -- it is never
    touched by `apply_submitted_purchase_order_approval`/`_rejection`, nor by
    `ItemMasterService.get_item_for_internal_use`.

    `item_service` IS constructed for real, because `apply_submitted_purchase_order_approval`
    genuinely calls `self._item_service.get_item_for_internal_use(...)` (directly, and via the
    `_adjust_on_order_balance`/`_require_requisition_line`-adjacent code paths). That method only
    reads `owner._item_repo` and `owner._tenant_context_service`, so `party_service` and
    `document_integration_service` -- both required-looking constructor parameters on
    `ItemMasterService` -- are passed as `None`: they are never touched by the one method this
    family actually calls, and building real ones would require pulling in `PartyService`'s and
    `DocumentIntegrationService`'s own repository graphs for no behavioral benefit.

    `reference_service`, `inventory_service`, and `stock_service` are passed as `None` on
    `PurchasingService` -- confirmed by reading `apply_submitted_purchase_order_approval`/
    `_rejection` and every private helper they call
    (`_adjust_on_order_balance`/`_require_requisition_line`/`_refresh_requisition_status`) in
    full: none of them ever touch `self._reference_service`/`self._inventory_service`/
    `self._stock_service`. `procurement_financial_outbox_service` and
    `document_integration_service` are `None` for the same reason -- both are only used by
    `post_receipt`/document-linking, never by approval apply or reject. `approval_service=None`
    for the same reason as every other family: the apply path never calls back into
    `ApprovalService`.
    """
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
