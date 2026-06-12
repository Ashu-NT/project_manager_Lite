from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.auth.domain import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
    UserRoleBinding,
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


class AuthSessionRepository(ABC):
    @abstractmethod
    def add(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def update(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> AuthSession | None: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> list[AuthSession]: ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> None: ...

    @abstractmethod
    def get(self, role_id: str) -> Role | None: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    def list_all(self) -> list[Role]: ...


class PermissionRepository(ABC):
    @abstractmethod
    def add(self, permission: Permission) -> None: ...

    @abstractmethod
    def get(self, permission_id: str) -> Permission | None: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Permission | None: ...

    @abstractmethod
    def list_all(self) -> list[Permission]: ...


class UserRoleRepository(ABC):
    @abstractmethod
    def add(self, binding: UserRoleBinding) -> None: ...

    @abstractmethod
    def delete(self, user_id: str, role_id: str, organization_id: str | None = None) -> None: ...

    @abstractmethod
    def exists(self, user_id: str, role_id: str, organization_id: str | None = None) -> bool: ...

    @abstractmethod
    def list_role_ids(self, user_id: str) -> list[str]: ...

    def list_role_ids_for_organization(self, user_id: str, organization_id: str) -> list[str]:
        return []


class RolePermissionRepository(ABC):
    @abstractmethod
    def add(self, binding: RolePermissionBinding) -> None: ...

    @abstractmethod
    def delete(self, role_id: str, permission_id: str) -> None: ...

    @abstractmethod
    def exists(self, role_id: str, permission_id: str) -> bool: ...

    @abstractmethod
    def list_permission_ids(self, role_id: str) -> list[str]: ...


__all__ = [
    "AuthSessionRepository",
    "PermissionRepository",
    "RolePermissionRepository",
    "RoleRepository",
    "UserRepository",
    "UserRoleRepository",
]
