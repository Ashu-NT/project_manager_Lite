from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.party.contracts import PartyRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class PartyUnitOfWork(UnitOfWork, Protocol):
    parties: PartyRepository
    _enterprise_audit_service: EnterpriseAuditService


class PartyUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> PartyUnitOfWork: ...  # type: ignore[override]


__all__ = ["PartyUnitOfWork", "PartyUnitOfWorkFactory"]
