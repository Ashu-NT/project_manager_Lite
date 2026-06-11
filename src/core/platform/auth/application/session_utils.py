from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.core.platform.auth.policy import session_timeout_minutes
from src.core.platform.common.exceptions import ValidationError

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount


def normalize_device_label(device_label: str | None) -> str | None:
    value = str(device_label or "").strip()
    return value or None


def validate_session_timeout_override(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Session timeout override must be an integer number of minutes.",
            code="AUTH_SESSION_TIMEOUT_INVALID",
        ) from exc
    if normalized < 5 or normalized > 1_440:
        raise ValidationError(
            "Session timeout override must be between 5 and 1440 minutes.",
            code="AUTH_SESSION_TIMEOUT_INVALID",
        )
    return normalized


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
