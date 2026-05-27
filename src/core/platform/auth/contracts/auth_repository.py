from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

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
    def get(self, user_id: str) -> Optional[UserAccount]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserAccount]: ...

    @abstractmethod
    def get_by_federated_identity(
        self,
        identity_provider: str,
        federated_subject: str,
    ) -> Optional[UserAccount]: ...

    @abstractmethod
    def list_all(self) -> List[UserAccount]: ...


class AuthSessionRepository(ABC):
    @abstractmethod
    def add(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def update(self, auth_session: AuthSession) -> None: ...

    @abstractmethod
    def get(self, session_id: str) -> Optional[AuthSession]: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[AuthSession]: ...


class RoleRepository(ABC):
    @abstractmethod
    def add(self, role: Role) -> None: ...

    @abstractmethod
    def get(self, role_id: str) -> Optional[Role]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Role]: ...

    @abstractmethod
    def list_all(self) -> List[Role]: ...


class PermissionRepository(ABC):
    @abstractmethod
    def add(self, permission: Permission) -> None: ...

    @abstractmethod
    def get(self, permission_id: str) -> Optional[Permission]: ...

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Permission]: ...

    @abstractmethod
    def list_all(self) -> List[Permission]: ...


class UserRoleRepository(ABC):
    @abstractmethod
    def add(self, binding: UserRoleBinding) -> None: ...

    @abstractmethod
    def delete(self, user_id: str, role_id: str) -> None: ...

    @abstractmethod
    def exists(self, user_id: str, role_id: str) -> bool: ...

    @abstractmethod
    def list_role_ids(self, user_id: str) -> List[str]: ...


class RolePermissionRepository(ABC):
    @abstractmethod
    def add(self, binding: RolePermissionBinding) -> None: ...

    @abstractmethod
    def delete(self, role_id: str, permission_id: str) -> None: ...

    @abstractmethod
    def exists(self, role_id: str, permission_id: str) -> bool: ...

    @abstractmethod
    def list_permission_ids(self, role_id: str) -> List[str]: ...


__all__ = [
    "AuthSessionRepository",
    "PermissionRepository",
    "RolePermissionRepository",
    "RoleRepository",
    "UserRepository",
    "UserRoleRepository",
]
