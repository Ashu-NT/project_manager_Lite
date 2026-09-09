from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class OrganizationUnitOfWork(UnitOfWork, Protocol):
    organizations: OrganizationRepository
    # record_audit_entry() resolves the audit service via getattr(owner, "_enterprise_audit_service", None).
    _enterprise_audit_service: EnterpriseAuditService


class OrganizationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> OrganizationUnitOfWork: ...  # type: ignore[override]


__all__ = ["OrganizationUnitOfWork", "OrganizationUnitOfWorkFactory"]
