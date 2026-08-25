"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): module-owned, session-parameterized approval
transaction participant for `purchase_requisition.submit`.

Design note (discovered during Step 1 implementation, not assumed up front): unlike PM's
financial services (e.g. Budget), a repo-wide grep confirmed
`ProcurementApprovalMixin.apply_submitted_requisition_approval`/`apply_submitted_requisition_rejection`
have EXACTLY ONE caller each -- the registration in `inventory_registry.py`. There is no separate
"direct apply" path for Inventory the way PM's financial families have one, so there is no risk of
this participant drifting from a parallel direct-apply method. Even so, this participant uses the
SAME fresh-instance-and-delegate pattern as every other family (construct a fresh
`ProcurementService`, call its existing, unmodified, already-public methods) rather than extracting
the method bodies as free functions -- this keeps all eight approval families structurally
consistent, and `apply_submitted_requisition_approval`/`_rejection` are public methods already, so
there is no reason to reshape them.

The fresh `ProcurementService` is bound to whichever Session
`build_procurement_approval_deps(session, ...)` was called with -- never the long-lived,
permanently shared-Session instance `inventory_registry.py` builds at startup. This is what makes
the approval-facing call genuinely session-parameterizable: given Session A it acts against A;
given Session B, against B; it never touches the startup Session by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.inventory_procurement.application.procurement.service import (
    ProcurementService,
)
from src.core.platform.contract.models.approval.contracts import ApprovalHandlerResult
from src.core.platform.domain.approval import ApprovalRequest


@dataclass(frozen=True)
class ProcurementApprovalDeps:
    """`procurement_service` is a fresh `ProcurementService`, bound to the Session
    `build_procurement_approval_deps(session, ...)` was called with, constructed with
    `approval_service=None` -- the apply path never calls back into `ApprovalService`. It is also
    constructed with `inventory_service=None`, `item_service=None`, `party_service=None`, and
    (via the constructor default) `activity_service=None` -- confirmed by reading
    `ProcurementApprovalMixin.apply_submitted_requisition_approval`/`_rejection` in full: they only
    touch `self._requisition_repo`, `self._requisition_line_repo`, and `record_activity(self, ...)`.
    `record_activity`'s `getattr(owner, "_activity_service", None)` is a silent no-op when that
    attribute is `None` -- and the CURRENT, unmodified, long-lived `ProcurementService` built in
    `inventory_registry.py`'s `build_inventory_procurement_service_bundle` is *also* constructed
    without an `activity_service=` kwarg, so this reproduces existing production behavior exactly,
    not a regression."""

    procurement_service: ProcurementService


class ProcurementApprovalParticipant:
    def apply(
        self, request: ApprovalRequest, deps: ProcurementApprovalDeps
    ) -> ApprovalHandlerResult:
        return deps.procurement_service.apply_submitted_requisition_approval(request)

    def reject(
        self, request: ApprovalRequest, deps: ProcurementApprovalDeps
    ) -> ApprovalHandlerResult:
        return deps.procurement_service.apply_submitted_requisition_rejection(request)


__all__ = ["ProcurementApprovalDeps", "ProcurementApprovalParticipant"]
