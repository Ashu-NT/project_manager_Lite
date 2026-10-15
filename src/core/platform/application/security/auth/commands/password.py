from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.auth_validation_policy import (
    AuthValidationPolicy,
)
from src.core.platform.application.security.auth.dto.commands.users import (
    UserPasswordResetCommand,
)
from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.security.auth.session.session_utils import (
    next_session_expiry,
    rotate_session_revision,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.domain.security.auth.credentials.passwords import (
    hash_password,
    verify_password,
)
from src.core.platform.domain.security.auth.events import (
    PasswordChanged,
    PasswordChangeType,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class PasswordCommandHandler:
    """Password changes and administrative resets; revokes persisted sessions and
    refreshes the current principal in the same transaction."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        auth_queries: AuthQueryHandler,
        user_repo: UserRepository,
        user_session: UserSessionContext | None,
        validation_policy: AuthValidationPolicy,
        target_users: TargetUserAuthorization,
        audit: SecurityAuditRecorder,
        lifecycle: AuthSessionLifecycle,
    ) -> None:
        self._tx = tx
        self._auth_queries = auth_queries
        self._user_repo = user_repo
        self._user_session = user_session
        self._validation_policy = validation_policy
        self._target_users = target_users
        self._audit = audit
        self._lifecycle = lifecycle

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        self._target_users.require_self_target(
            user_id,
            operation_label="change password",
        )
        user = self._auth_queries.require_user(user_id)
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect.", code="AUTH_FAILED")
        self._validation_policy.validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        user.password_changed_at = user.updated_at
        user.must_change_password = False
        rotate_session_revision(user)
        user.session_expires_at = next_session_expiry(user.updated_at, user=user)
        self._lifecycle.revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._persist_password_mutation(
            user,
            action="password.change",
            change_type=PasswordChangeType.CHANGED,
        )
        self._lifecycle.refresh_current_session_if_user(user.id)

    def force_user_password_reset(self, user_id: str) -> None:
        require_permission(self._user_session, "auth.manage", operation_label="force password reset")
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="force password reset",
        )
        user = self._auth_queries.require_user(user_id)
        user.must_change_password = True
        user.updated_at = datetime.now(UTC)
        rotate_session_revision(user)
        self._lifecycle.revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._persist_password_mutation(
            user,
            action="password.force_reset",
            change_type=PasswordChangeType.FORCE_RESET_REQUIRED,
        )

    def reset_user_password(self, command: UserPasswordResetCommand) -> UserAccount:
        user_id = command.user_id
        new_password = command.new_password
        require_permission(self._user_session, "auth.manage", operation_label="reset user password")
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="reset password",
        )
        user = self._auth_queries.require_user(user_id)
        self._validation_policy.validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(UTC)
        user.password_changed_at = user.updated_at
        user.must_change_password = True
        rotate_session_revision(user)
        user.session_expires_at = next_session_expiry(user.updated_at, user=user)
        self._lifecycle.revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        self._persist_password_mutation(
            user,
            action="password.reset",
            change_type=PasswordChangeType.RESET,
        )
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def _persist_password_mutation(
        self,
        user: UserAccount,
        *,
        action: str,
        change_type: PasswordChangeType,
    ) -> None:
        occurred_at = user.updated_at or datetime.now(UTC)
        with self._tx.uow() as uow:
            self._user_repo.update(user)
            self._audit.add_atomic_security_audit(
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
                    tenant_id=self._tx.active_tenant_id_for_event(),
                    change_type=change_type,
                    occurred_at=occurred_at,
                )
            )
            uow.commit()


__all__ = ["PasswordCommandHandler"]
