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
