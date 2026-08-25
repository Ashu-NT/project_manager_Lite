"""P4C (Platform Runtime Organization Provisioning Transaction Convergence): the narrow,
Platform-owned extension of the P3 canonical `UnitOfWork` that
`PlatformRuntimeApplicationService.provision_organization` uses.

A sibling of `OrganizationUnitOfWork` and `PlatformUnitOfWork`, not a growth of either --
ADR-005 Section 9/24 rejects a single Platform-wide UoW that accumulates one named accessor per
capability. Provisioning is its own orchestration operation with a genuine, atomic cross-capability
write set (an Organization row plus that organization's module entitlement rows plus their shared
audit trail), so it gets its own narrow UoW with exactly the two typed accessors it needs --
`organizations` and `entitlements` -- never a generic `repository_for`/`resolve` lookup.
"""

from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.contract.repositories.tenant.modules.contracts import (
    ModuleEntitlementRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class PlatformProvisioningUnitOfWork(UnitOfWork, Protocol):
    organizations: OrganizationRepository
    entitlements: ModuleEntitlementRepository
    # Named with a leading underscore, matching `PlatformUnitOfWork`/`OrganizationUnitOfWork`'s own
    # field name, because `record_audit_entry(owner, ...)`
    # (src/core/shared/audit/audit_recorder.py) resolves its `owner` argument's audit service via
    # `getattr(owner, "_enterprise_audit_service", None)`.
    _enterprise_audit_service: EnterpriseAuditService


class PlatformProvisioningUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> PlatformProvisioningUnitOfWork: ...  # type: ignore[override]


__all__ = ["PlatformProvisioningUnitOfWork", "PlatformProvisioningUnitOfWorkFactory"]
