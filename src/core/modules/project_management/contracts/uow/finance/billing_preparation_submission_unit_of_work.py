from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class BillingPreparationSubmissionUnitOfWork(UnitOfWork, Protocol):
    billing: ProjectBillingRepository
    approvals: ApprovalRepository
    _enterprise_audit_service: EnterpriseAuditService


class BillingPreparationSubmissionUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> BillingPreparationSubmissionUnitOfWork: ...  # type: ignore[override]


__all__ = [
    "BillingPreparationSubmissionUnitOfWork",
    "BillingPreparationSubmissionUnitOfWorkFactory",
]
