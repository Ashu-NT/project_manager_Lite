"""P5B prerequisite (Module Entitlement Transaction Convergence): `ModuleEntitlementUnitOfWork`
-- the narrow, Platform-owned extension of the P3 canonical `UnitOfWork` that
`ModuleCatalogService.set_module_state` uses.

A sibling of `OrganizationUnitOfWork`/`PlatformUnitOfWork`/`PlatformProvisioningUnitOfWork`, not a
growth of any of them -- ADR-005 Section 9/24 rejects a single Platform-wide UoW that accumulates
one named accessor per capability. Module Entitlements get their own narrow UoW with exactly the
one typed accessor `set_module_state` needs -- `entitlements` -- never a generic
`repository_for`/`resolve` lookup.
"""

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
    # Named with a leading underscore, matching every sibling Platform UoW's own field name,
    # because `record_audit_entry(owner, ...)` (src/core/shared/audit/audit_recorder.py) resolves
    # its `owner` argument's audit service via `getattr(owner, "_enterprise_audit_service", None)`.
    _enterprise_audit_service: EnterpriseAuditService


class ModuleEntitlementUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> ModuleEntitlementUnitOfWork: ...  # type: ignore[override]


__all__ = ["ModuleEntitlementUnitOfWork", "ModuleEntitlementUnitOfWorkFactory"]
