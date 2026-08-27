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
