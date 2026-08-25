"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `purchase_order.submit` (Purchasing family).

Design note (mirrors `procurement_apply_participant.py`): a repo-wide grep confirmed
`PurchasingReceivingMixin.apply_submitted_purchase_order_approval`/
`apply_submitted_purchase_order_rejection` have EXACTLY ONE caller each -- the registration in
`inventory_registry.py`. There is no separate "direct apply" path for this family. Even so, this
participant uses the SAME fresh-instance-and-delegate pattern as every other family (construct a
fresh `PurchasingService`, call its existing, unmodified, already-public methods) rather than
extracting the method bodies as free functions -- this keeps all eight approval families
structurally consistent.

The fresh `PurchasingService` is bound to whichever Session
`build_purchasing_approval_deps(session, ...)` was called with -- never the long-lived,
permanently shared-Session instance `inventory_registry.py` builds at startup. This is what makes
the approval-facing call genuinely session-parameterizable: given Session A it acts against A;
given Session B, against B; it never touches the startup Session by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.inventory_procurement.application.procurement.purchasing_service import (
    PurchasingService,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class PurchasingApprovalDeps:
    """`purchasing_service` is a fresh `PurchasingService`, bound to the Session
    `build_purchasing_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService`.

    Confirmed by reading `apply_submitted_purchase_order_approval`/`_rejection` (and every private
    helper they call: `_adjust_on_order_balance`, `_require_requisition_line`,
    `_refresh_requisition_status`) in full: they only touch `self._purchase_order_repo`,
    `self._purchase_order_line_repo`, `self._balance_repo`, `self._requisition_repo`,
    `self._requisition_line_repo`, `self._item_service.get_item_for_internal_use(...)`, and
    `record_activity(self, ...)`. Every repository above is therefore constructed fresh and real.
    `record_activity`'s `getattr(owner, "_activity_service", None)` is a silent no-op when that
    attribute is `None` -- `PurchasingService.__init__`'s own default for `activity_service` -- so
    leaving it unset reproduces existing production behavior exactly.

    `item_service` IS constructed for real (a fresh `ItemMasterService`) because
    `get_item_for_internal_use` is genuinely called -- but that method only touches
    `owner._item_repo` and `owner._tenant_context_service` (via `_active_organization`), never
    `party_service`/`document_integration_service`/`organization_repo`/`category_repo`, so those
    are passed as `None` on the fresh `ItemMasterService` too.

    `reference_service`, `inventory_service`, and `stock_service` are constructed as `None` --
    none of them play any role for this family: neither apply/reject method nor any helper they
    call ever touches `self._reference_service`/`self._inventory_service`/`self._stock_service`.
    `procurement_financial_outbox_service` and `document_integration_service` are `None` for the
    same reason -- they are only used by `post_receipt`/document-linking, never by approval apply
    or reject. `organization_repo` is likewise never touched by this flow (or by
    `ItemMasterService.get_item_for_internal_use`), so it is threaded through only for structural
    consistency with the other approval-apply factories, defaulting to `None`.
    """

    purchasing_service: PurchasingService


class PurchasingApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: PurchasingApprovalDeps
    ) -> ApprovalHandlerResult:
        return deps.purchasing_service.apply_submitted_purchase_order_approval(request)

    def reject(
        self, request: ApprovalRequest, deps: PurchasingApprovalDeps
    ) -> ApprovalHandlerResult:
        return deps.purchasing_service.apply_submitted_purchase_order_rejection(request)


__all__ = ["PurchasingApprovalDeps", "PurchasingApprovalParticipant"]
