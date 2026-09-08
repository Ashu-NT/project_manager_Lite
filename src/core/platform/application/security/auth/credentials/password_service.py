from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.domain.security.auth.credentials.passwords import hash_password, verify_password
from src.core.platform.domain.security.auth.events import PasswordChangeType, PasswordChanged
from src.core.platform.common.exceptions import ValidationError

from src.core.platform.application.security.auth.session.session_service import refresh_current_session_if_user, revoke_all_persisted_sessions
from src.core.platform.application.security.auth.audit.security_audit import add_atomic_security_audit
from src.core.platform.application.security.auth.session.session_utils import next_session_expiry, rotate_session_revision
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    require_self_target,
    require_target_user_in_active_tenant,
)

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount

    from src.core.platform.application.security.auth.auth_service import AuthService


def change_password(service: AuthService, user_id: str, current_password: str, new_password: str) -> None:
    require_self_target(
        service,
        user_id,
        operation_label="change password",
    )
    user = service._require_user(user_id)
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Current password is incorrect.", code="AUTH_FAILED")
    service._validate_password(new_password)
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    user.password_changed_at = user.updated_at
    user.must_change_password = False
    rotate_session_revision(user)
    user.session_expires_at = next_session_expiry(user.updated_at, user=user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    _persist_password_mutation(
        service,
        user,
        action="password.change",
        change_type=PasswordChangeType.CHANGED,
    )
    refresh_current_session_if_user(service, user.id)


def force_user_password_reset(service: AuthService, user_id: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="force password reset")
    require_target_user_in_active_tenant(
        service,
        user_id,
        operation_label="force password reset",
    )
    user = service._require_user(user_id)
    user.must_change_password = True
    user.updated_at = datetime.now(timezone.utc)
    rotate_session_revision(user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    _persist_password_mutation(
        service,
        user,
        action="password.force_reset",
        change_type=PasswordChangeType.FORCE_RESET_REQUIRED,
    )


def reset_user_password(service: AuthService, user_id: str, new_password: str) -> UserAccount:
    require_permission(service._user_session, "auth.manage", operation_label="reset user password")
    require_target_user_in_active_tenant(
        service,
        user_id,
        operation_label="reset password",
    )
    user = service._require_user(user_id)
    service._validate_password(new_password)
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    user.password_changed_at = user.updated_at
    user.must_change_password = True
    rotate_session_revision(user)
    user.session_expires_at = next_session_expiry(user.updated_at, user=user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    _persist_password_mutation(
        service,
        user,
        action="password.reset",
        change_type=PasswordChangeType.RESET,
    )
    refresh_current_session_if_user(service, user.id)
    return user


def _persist_password_mutation(
    service: AuthService,
    user: UserAccount,
    *,
    action: str,
    change_type: PasswordChangeType,
) -> None:
    occurred_at = user.updated_at or datetime.now(timezone.utc)
    with service._uow() as uow:
        service._user_repo.update(user)
        add_atomic_security_audit(
            service,
            operation="update",
            entity_type="user",
            entity_id=user.id,
            action=action,
            severity="high",
            field="password",
        )
        uow.record_event(
            PasswordChanged(
                user_id=user.id,
                tenant_id=service._active_tenant_id_for_event(),
                change_type=change_type,
                occurred_at=occurred_at,
            )
        )
        uow.commit()


__all__ = ["change_password", "force_user_password_reset", "reset_user_password"]
