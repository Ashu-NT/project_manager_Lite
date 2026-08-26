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
from src.core.modules.inventory_procurement.contracts.persistence.requisition_submission_unit_of_work import (
    RequisitionSubmissionUnitOfWorkFactory,
)
from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
)
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
    require_tenant_context_service,
)
from src.core.shared.time.clock import Clock


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
        requisition_submission_uow_factory: RequisitionSubmissionUnitOfWorkFactory | None = None,
        clock: Clock | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session=None,
        activity_service=None,
    ) -> None:
        self._session: Session = session
        self._requisition_repo: PurchaseRequisitionRepository = requisition_repo
        self._requisition_line_repo: PurchaseRequisitionLineRepository = requisition_line_repo
        self._organization_repo: OrganizationRepository = organization_repo
        self._tenant_context_service: TenantContextService = require_tenant_context_service(
            tenant_context_service,
            consumer_label="ProcurementService",
        )
        self._inventory_service: InventoryService = inventory_service
        self._item_service: ItemMasterService = item_service
        self._party_service: PartyService = party_service
        self._approval_service: ApprovalService = approval_service
        self._requisition_submission_uow_factory: RequisitionSubmissionUnitOfWorkFactory = (
            requisition_submission_uow_factory
        )
        # Approval-P2: `occurred_at` on the `ApprovalRequested` recorded by `submit_requisition`
        # comes from this Clock, never `datetime.now()`. Optional only so this constructor stays
        # backward-compatible for the apply-participant's own fresh, submission-unrelated
        # `ProcurementService` instance (`build_procurement_approval_deps`, which never calls
        # `submit_requisition`); production composition always supplies a real `SystemClock()`.
        self._clock = clock
        self._user_session = user_session
        self._activity_service = activity_service


__all__ = ["ProcurementService"]
