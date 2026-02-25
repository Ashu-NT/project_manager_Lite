from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core.domain.identifiers import generate_id


@dataclass
class UserAccount:
    id: str
    username: str
    password_hash: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        username: str,
        password_hash: str,
        display_name: str | None = None,
        email: str | None = None,
        is_active: bool = True,
    ) -> "UserAccount":
        now = datetime.now(timezone.utc)
        return UserAccount(
            id=generate_id(),
            username=username,
            password_hash=password_hash,
            display_name=display_name,
            email=email,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class Role:
    id: str
    name: str
    description: str = ""
    is_system: bool = True

    @staticmethod
    def create(name: str, description: str = "", is_system: bool = True) -> "Role":
        return Role(
            id=generate_id(),
            name=name,
            description=description,
            is_system=is_system,
        )


@dataclass
class Permission:
    id: str
    code: str
    description: str = ""

    @staticmethod
    def create(code: str, description: str = "") -> "Permission":
        return Permission(
            id=generate_id(),
            code=code,
            description=description,
        )


@dataclass
class UserRoleBinding:
    id: str
    user_id: str
    role_id: str

    @staticmethod
    def create(user_id: str, role_id: str) -> "UserRoleBinding":
        return UserRoleBinding(
            id=generate_id(),
            user_id=user_id,
            role_id=role_id,
        )


@dataclass
class RolePermissionBinding:
    id: str
    role_id: str
    permission_id: str

    @staticmethod
    def create(role_id: str, permission_id: str) -> "RolePermissionBinding":
        return RolePermissionBinding(
            id=generate_id(),
            role_id=role_id,
            permission_id=permission_id,
        )


__all__ = [
    "UserAccount",
    "Role",
    "Permission",
    "UserRoleBinding",
    "RolePermissionBinding",
]
