from __future__ import annotations

from typing import Protocol

from src.core.modules.project_management.contracts.repositories.register.register import (
    RegisterEntryRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class RegisterUnitOfWork(UnitOfWork, Protocol):
    """One fresh transaction for `RegisterEntry` mutations -- the narrowest explicit UoW for this
    capability, since no existing PM UoW already owns the Register repository."""

    entries: RegisterEntryRepository
    _enterprise_audit_service: EnterpriseAuditService
    _activity_service: ActivityService


class RegisterUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> RegisterUnitOfWork: ...  # type: ignore[override]


__all__ = ["RegisterUnitOfWork", "RegisterUnitOfWorkFactory"]
