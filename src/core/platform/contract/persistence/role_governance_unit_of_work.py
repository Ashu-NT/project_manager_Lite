
from __future__ import annotations

from typing import Protocol

from src.core.platform.contract.repositories.history.audit.contracts import AuditRepository
from src.core.platform.contract.repositories.security.auth.auth_repository import (
    PermissionRepository,
    RoleBindingRepository,
    RoleDelegationPolicyRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class RoleGovernanceUnitOfWork(UnitOfWork, Protocol):
    role_bindings: RoleBindingRepository
    roles: RoleRepository
    role_delegation_policies: RoleDelegationPolicyRepository
    role_permissions: RolePermissionRepository
    permissions: PermissionRepository
    users: UserRepository
    tenants: TenantRepository
    memberships: UserTenantMembershipRepository
    audit: AuditRepository


class RoleGovernanceUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> RoleGovernanceUnitOfWork: ...  # type: ignore[override]


__all__ = ["RoleGovernanceUnitOfWork", "RoleGovernanceUnitOfWorkFactory"]
