from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserCreateCommand:
    username: str
    password: str
    display_name: str | None = None
    email: str | None = None
    is_active: bool = True


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
