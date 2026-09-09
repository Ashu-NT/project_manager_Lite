"""Narrow UoW `ModuleCatalogService.set_module_state` uses."""

from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.tenant.modules.contracts import (
    ModuleEntitlementRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class ModuleEntitlementUnitOfWork(UnitOfWork, Protocol):
    entitlements: ModuleEntitlementRepository
    # record_audit_entry() resolves the audit service via getattr(owner, "_enterprise_audit_service", None).
    _enterprise_audit_service: EnterpriseAuditService


class ModuleEntitlementUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> ModuleEntitlementUnitOfWork: ...  # type: ignore[override]


__all__ = ["ModuleEntitlementUnitOfWork", "ModuleEntitlementUnitOfWorkFactory"]
