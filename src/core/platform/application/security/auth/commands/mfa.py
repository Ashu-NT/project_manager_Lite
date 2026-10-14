from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.domain.security.auth.credentials.mfa import (
    generate_mfa_secret,
    verify_totp_code,
)
from src.core.platform.domain.security.auth.events import (
    MfaChangeType,
    MfaStatusChanged,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class MfaCommandHandler:
    """Multi-factor authentication lifecycle: provision a secret, enable after
    verification, disable."""

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

    def provision_mfa_secret(self, user_id: str) -> str:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="provision user mfa secret",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="provision MFA",
        )
        user = self._auth_queries.require_user(user_id)
        user.mfa_secret = generate_mfa_secret()
        user.mfa_enabled = False
        user.updated_at = datetime.now(UTC)
        self._persist_mfa_mutation(
            user,
            action="mfa.provision",
            severity="high",
            change_type=MfaChangeType.PROVISIONED,
        )
        self._lifecycle.refresh_current_session_if_user(user.id)
        return str(user.mfa_secret or "")

    def enable_user_mfa(self, user_id: str, verification_code: str) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="enable user mfa",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="enable MFA",
        )
        user = self._auth_queries.require_user(user_id)
        if not verify_totp_code(getattr(user, "mfa_secret", None), verification_code):
            raise ValidationError(
                "Invalid multi-factor authentication verification code.",
                code="AUTH_MFA_FAILED",
            )
        user.mfa_enabled = True
        user.updated_at = datetime.now(UTC)
        self._persist_mfa_mutation(
            user,
            action="mfa.enable",
            severity="medium",
            change_type=MfaChangeType.ENABLED,
        )
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def disable_user_mfa(self, user_id: str) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="disable user mfa",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="disable MFA",
        )
        user = self._auth_queries.require_user(user_id)
        user.mfa_enabled = False
        user.updated_at = datetime.now(UTC)
        self._persist_mfa_mutation(
            user,
            action="mfa.disable",
            severity="high",
            change_type=MfaChangeType.DISABLED,
        )
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def _persist_mfa_mutation(
        self,
        user: UserAccount,
        *,
        action: str,
        severity: str,
        change_type: MfaChangeType,
    ) -> None:
        occurred_at = user.updated_at or datetime.now(UTC)
        with self._tx.uow() as uow:
            self._user_repo.update(user)
            self._audit.add_atomic_security_audit(
                operation="update",
                entity_type="user",
                entity_id=user.id,
                action=action,
                severity=severity,
                field="mfa",
            )
            uow.record_event(
                MfaStatusChanged(
                    user_id=user.id,
                    tenant_id=self._tx.active_tenant_id_for_event(),
                    change_type=change_type,
                    occurred_at=occurred_at,
                )
            )
            uow.commit()


__all__ = ["MfaCommandHandler"]
