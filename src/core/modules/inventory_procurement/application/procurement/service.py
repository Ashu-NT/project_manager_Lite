from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.inventory import InventoryService
from src.core.modules.inventory_procurement.application.procurement.procurement_approval import (
    ProcurementApprovalMixin,
)
from src.core.modules.inventory_procurement.application.procurement.procurement_lifecycle import (
    ProcurementLifecycleMixin,
)
from src.core.modules.inventory_procurement.application.procurement.procurement_queries import (
    ProcurementQueryMixin,
)
from src.core.modules.inventory_procurement.application.procurement.procurement_support import (
    ProcurementSupportMixin,
)
from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
)
from src.core.platform.approval import ApprovalService
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.party import PartyService
from src.core.platform.tenancy.tenant_context import TenantContextService


class ProcurementService(
    ProcurementSupportMixin,
    ProcurementQueryMixin,
    ProcurementLifecycleMixin,
    ProcurementApprovalMixin,
):
    """Inventory requisition orchestration composed from focused mixins."""

    def __init__(
        self,
        session: Session,
        requisition_repo: PurchaseRequisitionRepository,
        requisition_line_repo: PurchaseRequisitionLineRepository,
        *,
        organization_repo: OrganizationRepository,
        inventory_service: InventoryService,
        item_service: ItemMasterService,
        party_service: PartyService,
        approval_service: ApprovalService,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._requisition_repo = requisition_repo
        self._requisition_line_repo = requisition_line_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = tenant_context_service or TenantContextService(
            organization_repo=organization_repo,
            user_session=user_session,
        )
        self._inventory_service = inventory_service
        self._item_service = item_service
        self._party_service = party_service
        self._approval_service = approval_service
        self._user_session = user_session
        self._audit_service = audit_service


__all__ = ["ProcurementService"]
