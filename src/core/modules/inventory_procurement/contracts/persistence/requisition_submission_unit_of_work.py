
from __future__ import annotations

from typing import Protocol

from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseRequisitionLineRepository,
    PurchaseRequisitionRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class RequisitionSubmissionUnitOfWork(UnitOfWork, Protocol):
    requisitions: PurchaseRequisitionRepository
    requisition_lines: PurchaseRequisitionLineRepository
    approvals: ApprovalRepository
    # Same leading-underscore name `record_audit_entry`'s owner-duck-type lookup requires --
    # see `PlatformUnitOfWork`'s own identical field for the full rationale.
    _enterprise_audit_service: EnterpriseAuditService


class RequisitionSubmissionUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> RequisitionSubmissionUnitOfWork: ...  # type: ignore[override]


__all__ = ["RequisitionSubmissionUnitOfWork", "RequisitionSubmissionUnitOfWorkFactory"]
