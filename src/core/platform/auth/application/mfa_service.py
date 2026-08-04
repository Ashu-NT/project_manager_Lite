from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_any_permission
from src.core.platform.auth.mfa import generate_mfa_secret, verify_totp_code
from src.core.platform.common.exceptions import ValidationError

from .session_service import refresh_current_session_if_user
from .security_audit import add_atomic_security_audit
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import require_target_user_in_active_tenant

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


def provision_mfa_secret(service: AuthService, user_id: str) -> str:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="provision user mfa secret",
    )
    require_target_user_in_active_tenant(
        service,
        user_id,
        operation_label="provision MFA",
    )
    user = service._require_user(user_id)
    user.mfa_secret = generate_mfa_secret()
    user.mfa_enabled = False
    user.updated_at = datetime.now(timezone.utc)
    _persist_mfa_mutation(
        service,
        user,
        action="mfa.provision",
        severity="high",
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return str(user.mfa_secret or "")


def enable_user_mfa(service: AuthService, user_id: str, verification_code: str) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="enable user mfa",
    )
    require_target_user_in_active_tenant(
        service,
        user_id,
        operation_label="enable MFA",
    )
    user = service._require_user(user_id)
    if not verify_totp_code(getattr(user, "mfa_secret", None), verification_code):
        raise ValidationError(
            "Invalid multi-factor authentication verification code.",
            code="AUTH_MFA_FAILED",
        )
    user.mfa_enabled = True
    user.updated_at = datetime.now(timezone.utc)
    _persist_mfa_mutation(
        service,
        user,
        action="mfa.enable",
        severity="medium",
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def disable_user_mfa(service: AuthService, user_id: str) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="disable user mfa",
    )
    require_target_user_in_active_tenant(
        service,
        user_id,
        operation_label="disable MFA",
    )
    user = service._require_user(user_id)
    user.mfa_enabled = False
    user.updated_at = datetime.now(timezone.utc)
    _persist_mfa_mutation(
        service,
        user,
        action="mfa.disable",
        severity="high",
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def _persist_mfa_mutation(
    service: AuthService,
    user: UserAccount,
    *,
    action: str,
    severity: str,
) -> None:
    try:
        service._user_repo.update(user)
        add_atomic_security_audit(
            service,
            operation="update",
            entity_type="user",
            entity_id=user.id,
            action=action,
            severity=severity,
            field="mfa",
        )
        service._session.commit()
    except Exception:
        service._session.rollback()
        raise


__all__ = ["disable_user_mfa", "enable_user_mfa", "provision_mfa_secret"]
