from __future__ import annotations

from typing import Protocol

from src.core.modules.inventory_procurement.contracts.repositories.procurement import (
    PurchaseOrderRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class PurchaseOrderSubmissionUnitOfWork(UnitOfWork, Protocol):
    purchase_orders: PurchaseOrderRepository
    approvals: ApprovalRepository
    _enterprise_audit_service: EnterpriseAuditService


class PurchaseOrderSubmissionUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> PurchaseOrderSubmissionUnitOfWork: ...  # type: ignore[override]


__all__ = ["PurchaseOrderSubmissionUnitOfWork", "PurchaseOrderSubmissionUnitOfWorkFactory"]
