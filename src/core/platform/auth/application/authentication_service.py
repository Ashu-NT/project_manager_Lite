from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.platform.auth.mfa import verify_totp_code
from src.core.platform.auth.passwords import verify_password
from src.core.platform.common.exceptions import ValidationError

from .authentication_transactions import (
    complete_successful_authentication,
    persist_standalone_login_denial,
    register_failed_login,
)
from .federated_identity_service import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


def authenticate(
    service: AuthService,
    username: str,
    raw_password: str,
    *,
    mfa_code: str | None = None,
    device_label: str | None = None,
) -> UserAccount:
    normalized = (username or "").strip().lower()
    now = datetime.now(timezone.utc)
    user = service._user_repo.get_by_username(normalized)
    if not user or not user.is_active:
        persist_standalone_login_denial(
            service,
            username=normalized,
            user=user,
            reason="invalid_credentials",
        )
        raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
    if user.locked_until is not None and user.locked_until <= now:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = now
    if user.locked_until is not None and user.locked_until > now:
        persist_standalone_login_denial(
            service,
            username=normalized,
            user=user,
            reason="locked_out",
            details={
                "locked_until": user.locked_until.isoformat(),
            },
        )
        raise ValidationError(
            f"Account is locked until {user.locked_until.isoformat()}.",
            code="AUTH_LOCKED",
        )
    if not verify_password(raw_password, user.password_hash):
        register_failed_login(
            service,
            user,
            username=normalized,
            occurred_at=now,
            reason="invalid_credentials",
        )
        raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
    if bool(getattr(user, "mfa_enabled", False)):
        if not verify_totp_code(
            getattr(user, "mfa_secret", None),
            mfa_code,
            at_time=now,
        ):
            reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
            register_failed_login(
                service,
                user,
                username=normalized,
                occurred_at=now,
                reason=reason,
            )
            message = (
                "Multi-factor authentication code is required."
                if reason == "mfa_required"
                else "Invalid multi-factor authentication code."
            )
            code = (
                "AUTH_MFA_REQUIRED"
                if reason == "mfa_required"
                else "AUTH_MFA_FAILED"
            )
            raise ValidationError(message, code=code)
    complete_successful_authentication(
        service,
        user,
        occurred_at=now,
        auth_method="password",
        device_label=device_label,
    )
    return user


def authenticate_federated(
    service: AuthService,
    *,
    identity_provider: str,
    federated_subject: str,
    mfa_code: str | None = None,
    device_label: str | None = None,
) -> UserAccount:
    normalized_provider = normalize_identity_provider(identity_provider)
    normalized_subject = normalize_federated_subject(federated_subject)
    validate_federated_identity(normalized_provider, normalized_subject)
    now = datetime.now(timezone.utc)
    user = service._user_repo.get_by_federated_identity(
        normalized_provider,
        normalized_subject,
    )
    audit_username = (
        user.username if user is not None else f"federated:{normalized_provider}"
    )
    if not user or not user.is_active:
        persist_standalone_login_denial(
            service,
            username=audit_username,
            user=user,
            reason="invalid_federated_identity",
            details={"identity_provider": normalized_provider},
        )
        raise ValidationError("Invalid federated identity.", code="AUTH_FAILED")
    if user.locked_until is not None and user.locked_until <= now:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = now
    if user.locked_until is not None and user.locked_until > now:
        persist_standalone_login_denial(
            service,
            username=audit_username,
            user=user,
            reason="locked_out",
            details={
                "locked_until": user.locked_until.isoformat(),
                "identity_provider": normalized_provider,
            },
        )
        raise ValidationError(
            f"Account is locked until {user.locked_until.isoformat()}.",
            code="AUTH_LOCKED",
        )
    if bool(getattr(user, "mfa_enabled", False)):
        if not verify_totp_code(
            getattr(user, "mfa_secret", None),
            mfa_code,
            at_time=now,
        ):
            reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
            register_failed_login(
                service,
                user,
                username=audit_username,
                occurred_at=now,
                reason=reason,
                auth_method=f"federated:{normalized_provider}",
            )
            message = (
                "Multi-factor authentication code is required."
                if reason == "mfa_required"
                else "Invalid multi-factor authentication code."
            )
            code = (
                "AUTH_MFA_REQUIRED"
                if reason == "mfa_required"
                else "AUTH_MFA_FAILED"
            )
            raise ValidationError(message, code=code)
    complete_successful_authentication(
        service,
        user,
        occurred_at=now,
        auth_method=f"federated:{normalized_provider}",
        device_label=device_label,
    )
    return user


__all__ = [
    "authenticate",
    "authenticate_federated",
    "complete_successful_authentication",
    "register_failed_login",
]
