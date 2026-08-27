from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class SiteUnitOfWork(UnitOfWork, Protocol):
    sites: SiteRepository
    _enterprise_audit_service: EnterpriseAuditService


class SiteUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> SiteUnitOfWork: ...  # type: ignore[override]


__all__ = ["SiteUnitOfWork", "SiteUnitOfWorkFactory"]
