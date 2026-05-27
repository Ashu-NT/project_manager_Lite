from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RoleDto:
    id: str
    name: str
    description: str
    is_system: bool


@dataclass(frozen=True)
class UserDto:
    id: str
    username: str
    display_name: str | None
    email: str | None
    identity_provider: str | None
    federated_subject: str | None
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    last_login_auth_method: str | None
    last_login_device_label: str | None
    session_expires_at: datetime | None
    session_timeout_minutes_override: int | None
    must_change_password: bool
    version: int
    role_names: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UserCreateCommand:
    username: str
    password: str
    display_name: str | None = None
    email: str | None = None
    is_active: bool = True
    role_names: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UserUpdateCommand:
    user_id: str
    username: str | None = None
    display_name: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class UserPasswordResetCommand:
    user_id: str
    new_password: str
