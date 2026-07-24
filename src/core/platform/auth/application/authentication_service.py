from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.domain import AuthSession
from src.core.platform.auth.mfa import verify_totp_code
from src.core.platform.auth.passwords import verify_password
from src.core.platform.auth.policy import login_lockout_minutes, login_lockout_threshold
from src.core.platform.common.exceptions import ValidationError

from .audit_recorder import record_auth_event
from .federated_identity_service import (
    normalize_federated_subject,
    normalize_identity_provider,
    validate_federated_identity,
)
from .session_service import refresh_current_session_if_user
from .session_utils import next_session_expiry, normalize_device_label

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService

logger = logging.getLogger(__name__)


def _current_session_context_for_user(service: AuthService, user_id: str) -> tuple[str | None, str | None]:
    if service._user_session is None:
        return None, None
    principal = service._user_session.principal
    if principal is None or principal.user_id != user_id:
        return None, None
    return (
        service._user_session.active_tenant_id(),
        service._user_session.active_organization_id(),
    )


def _preferred_restore_session(service: AuthService, user: UserAccount) -> AuthSession | None:
    if service._auth_session_repo is None:
        return None
    active_session_id = str(getattr(user, "active_session_id", "") or "").strip() or None
    if active_session_id is not None:
        auth_session = service._auth_session_repo.get(active_session_id)
        if auth_session is not None:
            return auth_session
    sessions = service._auth_session_repo.list_by_user(user.id)
    for auth_session in sessions:
        if auth_session.revoked_at is None:
            return auth_session
    return sessions[0] if sessions else None


def _resolve_last_active_context(service: AuthService, user: UserAccount) -> tuple[str | None, str | None]:
    active_tenant_id, active_organization_id = _current_session_context_for_user(service, user.id)
    if active_tenant_id is not None or active_organization_id is not None:
        return active_tenant_id, active_organization_id
    restore_session = _preferred_restore_session(service, user)
    if restore_session is None:
        return None, None
    return (
        str(getattr(restore_session, "last_active_tenant_id", "") or "").strip() or None,
        str(getattr(restore_session, "last_active_organization_id", "") or "").strip() or None,
    )


def complete_successful_authentication(
    service: AuthService,
    user: UserAccount,
    *,
    occurred_at: datetime,
    auth_method: str,
    device_label: str | None,
) -> None:
    last_active_tenant_id, last_active_organization_id = _resolve_last_active_context(service, user)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = occurred_at
    user.last_login_auth_method = auth_method
    user.last_login_device_label = normalize_device_label(device_label)
    user.session_expires_at = next_session_expiry(occurred_at, user=user)
    user.updated_at = occurred_at
    if service._auth_session_repo is not None:
        auth_session = AuthSession.create(
            user_id=user.id,
            session_revision=int(getattr(user, "session_revision", 1) or 1),
            auth_method=auth_method,
            expires_at=user.session_expires_at,
            device_label=user.last_login_device_label,
            last_active_tenant_id=last_active_tenant_id,
            last_active_organization_id=last_active_organization_id,
        )
        user.active_session_id = auth_session.id
        service._auth_session_repo.add(auth_session)
    else:
        user.active_session_id = None
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    record_auth_event(
        service,
        action="auth.login.success",
        username=user.username,
        user_id=user.id,
        details={
            "result": "ok",
            "auth_method": auth_method,
            "identity_provider": str(getattr(user, "identity_provider", "") or ""),
            "device_label": str(getattr(user, "last_login_device_label", "") or ""),
            "session_expires_at": user.session_expires_at.isoformat() if user.session_expires_at else "",
        },
    )
    refresh_current_session_if_user(service, user.id)


def register_failed_login(
    service: AuthService,
    user: UserAccount,
    *,
    username: str,
    occurred_at: datetime,
) -> None:
    user.failed_login_attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
    if user.failed_login_attempts >= login_lockout_threshold():
        user.locked_until = occurred_at + timedelta(minutes=login_lockout_minutes())
    user.updated_at = occurred_at
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    if user.locked_until is not None:
        logger.warning(
            "User '%s' locked out until %s after %s failed attempts.",
            username,
            user.locked_until.isoformat(),
            user.failed_login_attempts,
        )


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
        record_auth_event(
            service,
            action="auth.login.failed",
            username=normalized,
            user_id=user.id if user else None,
            details={"reason": "invalid_credentials"},
        )
        raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
    if user.locked_until is not None and user.locked_until <= now:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = now
        service._user_repo.update(user)
        service._session.commit()
        domain_events.auth_changed.emit(user.id)
    if user.locked_until is not None and user.locked_until > now:
        record_auth_event(
            service,
            action="auth.login.failed",
            username=normalized,
            user_id=user.id,
            details={
                "reason": "locked_out",
                "locked_until": user.locked_until.isoformat(),
            },
        )
        raise ValidationError(
            f"Account is locked until {user.locked_until.isoformat()}.",
            code="AUTH_LOCKED",
        )
    if not verify_password(raw_password, user.password_hash):
        register_failed_login(service, user, username=normalized, occurred_at=now)
        record_auth_event(
            service,
            action="auth.login.failed",
            username=normalized,
            user_id=user.id,
            details={
                "reason": "invalid_credentials",
                "failed_attempts": str(user.failed_login_attempts),
                "locked_until": user.locked_until.isoformat() if user.locked_until else "",
            },
        )
        raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
    if bool(getattr(user, "mfa_enabled", False)):
        if not verify_totp_code(getattr(user, "mfa_secret", None), mfa_code, at_time=now):
            register_failed_login(service, user, username=normalized, occurred_at=now)
            reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
            record_auth_event(
                service,
                action="auth.login.failed",
                username=normalized,
                user_id=user.id,
                details={"reason": reason},
            )
            message = (
                "Multi-factor authentication code is required."
                if reason == "mfa_required"
                else "Invalid multi-factor authentication code."
            )
            code = "AUTH_MFA_REQUIRED" if reason == "mfa_required" else "AUTH_MFA_FAILED"
            raise ValidationError(message, code=code)
    complete_successful_authentication(
        service, user, occurred_at=now, auth_method="password", device_label=device_label
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
    user = service._user_repo.get_by_federated_identity(normalized_provider, normalized_subject)
    audit_username = f"{normalized_provider}:{normalized_subject}"
    if not user or not user.is_active:
        record_auth_event(
            service,
            action="auth.login.failed",
            username=audit_username,
            user_id=user.id if user else None,
            details={"reason": "invalid_federated_identity"},
        )
        raise ValidationError("Invalid federated identity.", code="AUTH_FAILED")
    if user.locked_until is not None and user.locked_until <= now:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = now
        service._user_repo.update(user)
        service._session.commit()
        domain_events.auth_changed.emit(user.id)
    if user.locked_until is not None and user.locked_until > now:
        record_auth_event(
            service,
            action="auth.login.failed",
            username=audit_username,
            user_id=user.id,
            details={
                "reason": "locked_out",
                "locked_until": user.locked_until.isoformat(),
            },
        )
        raise ValidationError(
            f"Account is locked until {user.locked_until.isoformat()}.",
            code="AUTH_LOCKED",
        )
    if bool(getattr(user, "mfa_enabled", False)):
        if not verify_totp_code(getattr(user, "mfa_secret", None), mfa_code, at_time=now):
            register_failed_login(service, user, username=user.username, occurred_at=now)
            reason = "mfa_required" if not str(mfa_code or "").strip() else "mfa_invalid"
            record_auth_event(
                service,
                action="auth.login.failed",
                username=audit_username,
                user_id=user.id,
                details={"reason": reason},
            )
            message = (
                "Multi-factor authentication code is required."
                if reason == "mfa_required"
                else "Invalid multi-factor authentication code."
            )
            code = "AUTH_MFA_REQUIRED" if reason == "mfa_required" else "AUTH_MFA_FAILED"
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
