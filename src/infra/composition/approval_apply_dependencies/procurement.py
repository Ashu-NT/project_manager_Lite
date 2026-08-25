"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for
`purchase_requisition.submit` (Procurement family).

This is a plain function -- never a generic, type-keyed registry -- called explicitly at its own
`register_apply_handler` call site.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.procurement.service import (
    ProcurementService,
)
from src.core.modules.inventory_procurement.infrastructure.approval.procurement_apply_participant import (
    ProcurementApprovalDeps,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.repositories.procurement import (
    SqlAlchemyPurchaseRequisitionLineRepository,
    SqlAlchemyPurchaseRequisitionRepository,
)


def build_procurement_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    organization_repo=None,
) -> ProcurementApprovalDeps:
    """Every transaction-sensitive collaborator (both requisition repositories, and
    `ProcurementService` itself) is constructed fresh, bound to `session` -- never the caller's
    own, possibly different, Session. Unlike PM/Platform, Inventory does not build its
    repositories via `build_repository_bundle(session)` -- `inventory_registry.py` constructs
    `SqlAlchemyPurchaseRequisitionRepository`/`SqlAlchemyPurchaseRequisitionLineRepository`
    directly, inline, so this factory does the same, parameterized by the supplied `session`/
    `tenant_context_service` instead of a hardcoded `platform_services.session`.

    `user_session`/`tenant_context_service` are ambient, stateless-with-respect-to-this-transaction
    collaborators, passed through as-is (ADR-005 Section 24, Round 7's "ambient collaborators ...
    may be reused as-is" rule). `organization_repo` is accepted the same way, defaulting to `None`,
    for structural consistency with the other approval-apply factories -- it is never touched by
    `apply_submitted_requisition_approval`/`_rejection`.

    `inventory_service`, `item_service`, and `party_service` are NOT accepted as parameters here
    (unlike `organization_repo`) because they play no ambient-collaborator role for this family at
    all: confirmed by reading `ProcurementApprovalMixin.apply_submitted_requisition_approval`/
    `_rejection` in full, neither method ever touches
    `self._inventory_service`/`self._item_service`/`self._party_service`. `approval_service=None`
    for the same reason as every other family: the apply path never calls back into
    `ApprovalService`. `activity_service` is left at `ProcurementService.__init__`'s own default of
    `None` -- see `procurement_apply_participant.py`'s module/dataclass docstrings for why that
    reproduces current production behavior exactly.
    """
    requisition_repo = SqlAlchemyPurchaseRequisitionRepository(
        session, tenant_context_service=tenant_context_service
    )
    requisition_line_repo = SqlAlchemyPurchaseRequisitionLineRepository(
        session, tenant_context_service=tenant_context_service
    )
    procurement_service = ProcurementService(
        session,
        requisition_repo,
        requisition_line_repo,
        organization_repo=organization_repo,
        inventory_service=None,
        item_service=None,
        party_service=None,
        approval_service=None,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    return ProcurementApprovalDeps(procurement_service=procurement_service)


__all__ = ["build_procurement_approval_deps"]
