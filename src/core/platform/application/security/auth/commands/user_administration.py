from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.domain.security.auth import (
    UserAccount,
    normalize_auth_username,
)
from src.core.platform.domain.security.auth.events import (
    AccountUnlocked,
    UserAccountProfileUpdated,
    UserAccountStatusChanged,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class UserAdministrationCommandHandler:
    """Administrative account changes: activation, profile and lockout reset."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        auth_queries: AuthQueryHandler,
        user_repo: UserRepository,
        user_session: UserSessionContext | None,
        target_users: TargetUserAuthorization,
        audit: SecurityAuditRecorder,
        lifecycle: AuthSessionLifecycle,
    ) -> None:
        self._tx = tx
        self._auth_queries = auth_queries
        self._user_repo = user_repo
        self._user_session = user_session
        self._target_users = target_users
        self._audit = audit
        self._lifecycle = lifecycle

    def _enforce_user_tenant_boundary(self, target_user_id: str, operation: str) -> None:
        self._target_users.require_target_user_in_active_tenant(
            target_user_id,
            operation_label=operation,
        )

    def set_user_active(self, user_id: str, is_active: bool) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="set user active")
        self._enforce_user_tenant_boundary(user_id, "set active status")
        user = self._auth_queries.require_user(user_id)
        previous_is_active = user.is_active
        user.is_active = bool(is_active)
        user.updated_at = datetime.now(UTC)
        with self._tx.uow() as uow:
            self._user_repo.update(user)
            self._audit.add_atomic_security_audit(
                operation="update",
                entity_type="user",
                entity_id=user.id,
                action="user.set_active",
                severity="medium",
                field="is_active",
                old_value=str(previous_is_active),
                new_value=str(user.is_active),
            )
            if user.is_active != previous_is_active:
                uow.record_event(
                    UserAccountStatusChanged(
                        user_id=user.id,
                        tenant_id=self._tx.active_tenant_id_for_event(),
                        is_active=user.is_active,
                        occurred_at=user.updated_at,
                    )
                )
            uow.commit()
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def update_user_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        display_name: str | None = None,
        email: str | None = None,
    ) -> UserAccount:
        require_permission(self._user_session, "auth.manage", operation_label="update user profile")
        self._enforce_user_tenant_boundary(user_id, "update profile")
        user = self._auth_queries.require_user(user_id)
        if username is not None:
            normalized = normalize_auth_username(username)
            existing = self._user_repo.get_by_username(normalized)
            if existing and existing.id != user.id:
                raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
            user.username = username
        if display_name is not None:
            user.display_name = display_name
        if email is not None:
            user.email = email
        user.updated_at = datetime.now(UTC)
        try:
            with self._tx.uow() as uow:
                self._user_repo.update(user)
                self._audit.add_atomic_security_audit(
                    operation="update",
                    entity_type="user",
                    entity_id=user.id,
                    action="user.update_profile",
                    severity="low",
                    field="profile",
                )
                uow.record_event(
                    UserAccountProfileUpdated(
                        user_id=user.id,
                        tenant_id=self._tx.active_tenant_id_for_event(),
                        changed_fields=tuple(
                            name
                            for name, value in (
                                ("username", username),
                                ("display_name", display_name),
                                ("email", email),
                            )
                            if value is not None
                        ),
                        occurred_at=user.updated_at,
                    )
                )
                uow.commit()
        except IntegrityError as exc:
            if "username" in str(exc).lower():
                raise ValidationError("Username already exists.", code="USERNAME_EXISTS") from exc
            raise ValidationError(
                "Failed to update user due to data conflict.",
                code="USER_UPDATE_CONFLICT",
            ) from exc
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def unlock_user_account(self, user_id: str) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="unlock user account",
        )
        self._enforce_user_tenant_boundary(user_id, "unlock account")
        user = self._auth_queries.require_user(user_id)
        previous_failed_attempts = user.failed_login_attempts
        previous_locked_until = user.locked_until
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = datetime.now(UTC)
        with self._tx.uow() as uow:
            self._user_repo.update(user)
            self._audit.add_atomic_security_audit(
                operation="update",
                entity_type="user",
                entity_id=user.id,
                action="user.unlock_account",
                severity="medium",
                field="locked_until",
                metadata={
                    "previous_failed_login_attempts": previous_failed_attempts,
                },
            )
            if previous_failed_attempts > 0 or previous_locked_until is not None:
                uow.record_event(
                    AccountUnlocked(
                        user_id=user.id,
                        tenant_id=self._tx.active_tenant_id_for_event(),
                        occurred_at=user.updated_at,
                    )
                )
            uow.commit()
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user


__all__ = ["UserAdministrationCommandHandler"]
