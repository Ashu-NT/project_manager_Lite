from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_any_permission
from src.core.platform.auth.mfa import generate_mfa_secret, verify_totp_code
from src.core.platform.common.exceptions import ValidationError

from .session_service import refresh_current_session_if_user

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


def provision_mfa_secret(service: AuthService, user_id: str) -> str:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="provision user mfa secret",
    )
    user = service._require_user(user_id)
    user.mfa_secret = generate_mfa_secret()
    user.mfa_enabled = False
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return str(user.mfa_secret or "")


def enable_user_mfa(service: AuthService, user_id: str, verification_code: str) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="enable user mfa",
    )
    user = service._require_user(user_id)
    if not verify_totp_code(getattr(user, "mfa_secret", None), verification_code):
        raise ValidationError(
            "Invalid multi-factor authentication verification code.",
            code="AUTH_MFA_FAILED",
        )
    user.mfa_enabled = True
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def disable_user_mfa(service: AuthService, user_id: str) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="disable user mfa",
    )
    user = service._require_user(user_id)
    user.mfa_enabled = False
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


__all__ = ["disable_user_mfa", "enable_user_mfa", "provision_mfa_secret"]
