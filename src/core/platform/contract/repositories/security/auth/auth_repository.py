from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.core.platform.domain.security.auth import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
)
from src.core.platform.domain.security.authorization.roles import (
    AuthPolicyReconciliation,
    RoleBinding,
    RoleDelegationPolicy,
)


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: UserAccount) -> None: ...

    @abstractmethod
    def update(self, user: UserAccount) -> None: ...

    @abstractmethod
    def get(self, user_id: str) -> UserAccount | None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> UserAccount | None: ...

    @abstractmethod
    def get_by_federated_identity(
        self,
        identity_provider: str,
        federated_subject: str,
    ) -> UserAccount | None: ...

    @abstractmethod
    def list_all(self) -> list[UserAccount]: ...

    @abstractmethod
    def list_for_tenant(self, tenant_id: str) -> list[UserAccount]: ...


class AuthSessionRepository(ABC):
    @abstractmethod
    def add(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def update(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> AuthSession | None: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> list[AuthSession]: ...

    @abstractmethod
    def persist_context(
        self,
        session_id: str,
        *,
        last_active_tenant_id: str | None,
        last_active_organization_id: str | None,
        updated_at: datetime,
    ) -> bool: ...

    @abstractmethod
    def touch_validation(
        self,
        session_id: str,
        *,
        validated_at: datetime,
        throttle_seconds: int = 60,
    ) -> bool: ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> None: ...

    @abstractmethod
    def get(self, role_id: str) -> Role | None: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    def get_for_tenant_by_name(
        self,
        tenant_id: str,
        name: str,
        *,
        include_system: bool = True,
    ) -> Role | None: ...

    @abstractmethod
    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        include_system: bool = True,
    ) -> list[Role]: ...

    @abstractmethod
    def update_custom(
        self,
        role: Role,
        *,
        expected_policy_version: int,
    ) -> bool: ...

    @abstractmethod
    def set_policy_version(
        self,
        role_id: str,
        *,
        policy_version: int,
        updated_at: datetime,
    ) -> bool: ...

    @abstractmethod
    def list_all(self) -> list[Role]: ...


class RoleBindingRepository(ABC):
    @abstractmethod
    def add(self, binding: RoleBinding) -> None: ...

    @abstractmethod
    def get(self, binding_id: str) -> RoleBinding | None: ...

    @abstractmethod
    def list_active_for_principal(
        self,
        principal_id: str,
        *,
        tenant_id: str | None,
    ) -> list[RoleBinding]: ...

    @abstractmethod
    def list_active_for_role(
        self,
        role_id: str,
        *,
        tenant_id: str | None,
    ) -> list[RoleBinding]: ...

    @abstractmethod
    def list_active_for_role_across_tenants(
        self,
        role_id: str,
    ) -> list[RoleBinding]: ...

    @abstractmethod
    def get_active_for_assignment(
        self,
        *,
        principal_id: str,
        role_id: str,
        tenant_id: str | None,
        actual_scope_type: str,
        actual_scope_id: str | None,
    ) -> RoleBinding | None: ...

    @abstractmethod
    def revoke_expired_for_assignment(
        self,
        *,
        principal_id: str,
        role_id: str,
        tenant_id: str | None,
        actual_scope_type: str,
        actual_scope_id: str | None,
        as_of: datetime,
    ) -> int: ...

    @abstractmethod
    def revoke(self, binding_id: str, *, revoked_at: datetime) -> bool: ...

    @abstractmethod
    def revoke_active_for_principal_tenant(
        self,
        principal_id: str,
        tenant_id: str,
        *,
        revoked_at: datetime,
    ) -> int: ...

    @abstractmethod
    def revoke_active_for_role(
        self,
        role_id: str,
        tenant_id: str,
        *,
        revoked_at: datetime,
    ) -> int: ...


class RoleDelegationPolicyRepository(ABC):
    @abstractmethod
    def add(self, policy: RoleDelegationPolicy) -> None: ...

    @abstractmethod
    def get(self, policy_id: str) -> RoleDelegationPolicy | None: ...

    @abstractmethod
    def get_active_exact(
        self,
        *,
        actor_role_id: str,
        assignable_role_id: str,
        tenant_id: str | None,
        target_scope_type: str,
    ) -> RoleDelegationPolicy | None: ...

    @abstractmethod
    def find_active(
        self,
        *,
        actor_role_ids: set[str],
        assignable_role_id: str,
        tenant_id: str,
        target_scope_type: str,
    ) -> RoleDelegationPolicy | None: ...

    @abstractmethod
    def revoke(self, policy_id: str, *, revoked_at: datetime) -> bool: ...


class PermissionRepository(ABC):
    @abstractmethod
    def add(self, permission: Permission) -> None: ...

    @abstractmethod
    def get(self, permission_id: str) -> Permission | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Permission | None: ...

    @abstractmethod
    def list_all(self) -> list[Permission]: ...


class RolePermissionRepository(ABC):
    @abstractmethod
    def add(self, binding: RolePermissionBinding) -> None: ...

    @abstractmethod
    def delete(self, role_id: str, permission_id: str) -> None: ...

    @abstractmethod
    def exists(self, role_id: str, permission_id: str) -> bool: ...

    @abstractmethod
    def list_permission_ids(self, role_id: str) -> list[str]: ...


class AuthPolicyReconciliationRepository(ABC):
    @abstractmethod
    def add(self, reconciliation: AuthPolicyReconciliation) -> None: ...

    @abstractmethod
    def get_latest(
        self,
        policy_name: str,
        *,
        for_update: bool = False,
    ) -> AuthPolicyReconciliation | None: ...


__all__ = [
    "AuthPolicyReconciliationRepository",
    "AuthSessionRepository",
    "PermissionRepository",
    "RolePermissionRepository",
    "RoleBindingRepository",
    "RoleDelegationPolicyRepository",
    "RoleRepository",
    "UserRepository",
]
