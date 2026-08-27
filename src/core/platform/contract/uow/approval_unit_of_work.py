from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class PlatformUnitOfWork(UnitOfWork, Protocol):
    approvals: ApprovalRepository
    _enterprise_audit_service: EnterpriseAuditService


class PlatformUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> PlatformUnitOfWork: ...  # type: ignore[override]


__all__ = ["PlatformUnitOfWork", "PlatformUnitOfWorkFactory"]
