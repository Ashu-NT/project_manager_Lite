from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.core.platform.domain.security.auth import (
    normalize_auth_device_label,
    normalize_auth_session_timeout_override,
)
from src.core.platform.auth.policy import session_timeout_minutes

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


def normalize_device_label(device_label: str | None) -> str | None:
    return normalize_auth_device_label(device_label)


def validate_session_timeout_override(value: int | None) -> int | None:
    return normalize_auth_session_timeout_override(value)


def next_session_expiry(now: datetime, *, user: UserAccount | None = None) -> datetime:
    timeout_minutes = (
        validate_session_timeout_override(getattr(user, "session_timeout_minutes_override", None))
        if user is not None
        else None
    )
    return now + timedelta(minutes=timeout_minutes or session_timeout_minutes())


def rotate_session_revision(user: UserAccount) -> None:
    user.session_revision = max(1, int(getattr(user, "session_revision", 1) or 1)) + 1


__all__ = [
    "next_session_expiry",
    "normalize_device_label",
    "rotate_session_revision",
    "validate_session_timeout_override",
]
