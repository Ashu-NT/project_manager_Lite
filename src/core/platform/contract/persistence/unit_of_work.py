"""P4 Step 2 (ADR-005 Section 24, Round 7/8): `PlatformUnitOfWork` -- the narrow, Platform-owned
extension of the P3 canonical `UnitOfWork` that `ApprovalService`'s transaction-owning commands
(`request_change` when transaction-owning, `approve_and_apply`, `reject`) use.

Deliberately minimal, matching every other module-specific `UnitOfWork` extension's own
convention (ADR-005 Section 9: "a module-specific extension adds its own typed repository
accessors"): two named, typed fields -- `approvals` and `enterprise_audit_service` -- exactly
what `ApprovalService` itself needs, nothing more. Never gains a generic `repository_for(...)`,
`resolve(...)`, or any other open lookup -- that is the exact hidden-service-locator shape ADR-005
Section 9/24 already rejected. Business-module dependencies (a `budget_repo`, a `TaskService`,
etc.) never live here -- those come from the Step 1 module-owned `dependencies_factory(session)`,
called by `ApprovalService` with this UnitOfWork's own `session`, never from this protocol.
"""

from __future__ import annotations

from typing import Protocol

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.contract.repositories.approval.contracts import ApprovalRepository
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class PlatformUnitOfWork(UnitOfWork, Protocol):
    approvals: ApprovalRepository
    # Named with a leading underscore, matching every Step 1 `TDeps` dataclass's own field name,
    # because `record_audit_entry(owner, ...)` (src/core/shared/audit/audit_recorder.py) resolves
    # its `owner` argument's audit service via `getattr(owner, "_enterprise_audit_service", None)`
    # -- an existing, codebase-wide duck-type contract this protocol must match exactly so a
    # `PlatformUnitOfWork` instance can be passed as `record_audit_entry`'s `owner` directly.
    _enterprise_audit_service: EnterpriseAuditService


class PlatformUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> PlatformUnitOfWork: ...  # type: ignore[override]


__all__ = ["PlatformUnitOfWork", "PlatformUnitOfWorkFactory"]
