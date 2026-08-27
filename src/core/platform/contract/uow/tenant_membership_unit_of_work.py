from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.history.audit.contracts import AuditRepository
from src.core.platform.contract.repositories.security.auth.auth_repository import (
    AuthSessionRepository,
    RoleBindingRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class TenantMembershipUnitOfWork(UnitOfWork, Protocol):
    memberships: UserTenantMembershipRepository
    users: UserRepository
    tenants: TenantRepository
    roles: RoleRepository
    role_bindings: RoleBindingRepository
    auth_sessions: AuthSessionRepository
    audit: AuditRepository
    session: Session


class TenantMembershipUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> TenantMembershipUnitOfWork: ...  # type: ignore[override]


__all__ = ["TenantMembershipUnitOfWork", "TenantMembershipUnitOfWorkFactory"]
