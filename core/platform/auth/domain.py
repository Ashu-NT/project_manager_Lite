from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core.platform.common.ids import generate_id


@dataclass
class UserAccount:
    id: str
    username: str
    password_hash: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    identity_provider: Optional[str] = None
    federated_subject: Optional[str] = None
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    session_timeout_minutes_override: int | None = None
    session_revision: int = 1
    last_login_auth_method: Optional[str] = None
    last_login_device_label: Optional[str] = None
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    session_expires_at: datetime | None = None
    password_changed_at: datetime | None = None
    must_change_password: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1
    active_session_id: str | None = None

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
            identity_provider=None,
            federated_subject=None,
            mfa_secret=None,
            mfa_enabled=False,
            session_timeout_minutes_override=None,
            session_revision=1,
            last_login_auth_method=None,
            last_login_device_label=None,
            is_active=is_active,
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=None,
            session_expires_at=None,
            password_changed_at=now,
            must_change_password=False,
            created_at=now,
            updated_at=now,
            version=1,
            active_session_id=None,
        )


@dataclass
class AuthSession:
    id: str
    user_id: str
    session_revision: int
    auth_method: str
    device_label: Optional[str] = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    last_validated_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def create(
        *,
        user_id: str,
        session_revision: int,
        auth_method: str,
        expires_at: datetime,
        device_label: str | None = None,
    ) -> "AuthSession":
        now = datetime.now(timezone.utc)
        return AuthSession(
            id=generate_id(),
            user_id=user_id,
            session_revision=max(1, int(session_revision or 1)),
            auth_method=str(auth_method or "").strip() or "password",
            device_label=(str(device_label or "").strip() or None),
            issued_at=now,
            expires_at=expires_at,
            last_validated_at=now,
            revoked_at=None,
            created_at=now,
            updated_at=now,
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
    "AuthSession",
    "UserAccount",
    "Role",
    "Permission",
    "UserRoleBinding",
    "RolePermissionBinding",
]
