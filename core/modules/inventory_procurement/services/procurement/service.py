from __future__ import annotations

from sqlalchemy.orm import Session

from core.modules.inventory_procurement.interfaces import PurchaseRequisitionLineRepository, PurchaseRequisitionRepository
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.procurement.procurement_approval import ProcurementApprovalMixin
from core.modules.inventory_procurement.services.procurement.procurement_lifecycle import ProcurementLifecycleMixin
from core.modules.inventory_procurement.services.procurement.procurement_queries import ProcurementQueryMixin
from core.modules.inventory_procurement.services.procurement.procurement_support import ProcurementSupportMixin
from core.platform.approval import ApprovalService
from src.core.platform.org.contracts import OrganizationRepository
from core.platform.party import PartyService


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
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._requisition_repo = requisition_repo
        self._requisition_line_repo = requisition_line_repo
        self._organization_repo = organization_repo
        self._inventory_service = inventory_service
        self._item_service = item_service
        self._party_service = party_service
        self._approval_service = approval_service
        self._user_session = user_session
        self._audit_service = audit_service


__all__ = ["ProcurementService"]
