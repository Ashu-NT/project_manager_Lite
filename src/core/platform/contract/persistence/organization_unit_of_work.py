"""P4B (Organization Capability Transaction Convergence): `OrganizationUnitOfWork` -- the narrow,
Platform-owned extension of the P3 canonical `UnitOfWork` that `OrganizationService`'s
transaction-owning commands (`create_organization`, `update_organization`,
`set_active_organization`, `bootstrap_defaults`, when transaction-owning) use.

A sibling of `PlatformUnitOfWork` (Approval's own narrow extension), not a growth of it --
ADR-005 Section 9/24 rejects a single Platform-wide UoW that accumulates one named accessor per
capability (`uow.approvals`, `uow.organizations`, `uow.departments`, ...), since that is exactly
the hidden-service-locator shape already rejected. Each capability gets its own minimal
extension: two named, typed fields -- `organizations` and `_enterprise_audit_service` -- exactly
what `OrganizationService` itself needs, nothing more.
"""

from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class OrganizationUnitOfWork(UnitOfWork, Protocol):
    organizations: OrganizationRepository
    # Named with a leading underscore, matching `PlatformUnitOfWork`'s own field name, because
    # `record_audit_entry(owner, ...)` (src/core/shared/audit/audit_recorder.py) resolves its
    # `owner` argument's audit service via `getattr(owner, "_enterprise_audit_service", None)` --
    # an existing, codebase-wide duck-type contract this protocol must match exactly so an
    # `OrganizationUnitOfWork` instance can be passed as `record_audit_entry`'s `owner` directly.
    _enterprise_audit_service: EnterpriseAuditService


class OrganizationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> OrganizationUnitOfWork: ...  # type: ignore[override]


__all__ = ["OrganizationUnitOfWork", "OrganizationUnitOfWorkFactory"]
