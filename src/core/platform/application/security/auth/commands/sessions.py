from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import src.core.platform.application.security.auth.mappers.user as response_mapper
from src.core.platform.application.security.auth.dto.responses.user import UserDto
from src.core.platform.application.security.auth.session.session_utils import (
    next_session_expiry,
    rotate_session_revision,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.security.auth import AuthSession
from src.core.platform.domain.security.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.domain.security.auth.events import (
    UserSessionPolicyChanged,
    UserSessionsRevoked,
)
from src.core.platform.domain.security.auth.session import UserSessionPrincipal

logger = logging.getLogger(__name__)
_SESSION_VALIDATION_THROTTLE_SECONDS = 60
from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.queries.auth_queries import (
    AuthQueryHandler,
)
from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    TargetUserAuthorization,
)
from src.core.platform.contract.repositories.security.auth import (
    AuthSessionRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class AuthSessionCommandHandler:
    """Session governance writes: per-user session policy, revocations, context
    persistence and periodic validation of a restored principal."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        auth_queries: AuthQueryHandler,
        user_repo: UserRepository,
        auth_session_repo: AuthSessionRepository | None,
        user_session: UserSessionContext | None,
        target_users: TargetUserAuthorization,
        audit: SecurityAuditRecorder,
        lifecycle: AuthSessionLifecycle,
        principals: PrincipalBuilder,
    ) -> None:
        self._tx = tx
        self._auth_queries = auth_queries
        self._user_repo = user_repo
        self._auth_session_repo = auth_session_repo
        self._user_session = user_session
        self._target_users = target_users
        self._audit = audit
        self._lifecycle = lifecycle
        self._principals = principals

    def set_user_session_policy(
        self,
        user_id: str,
        *,
        session_timeout_minutes_override: int | None,
    ) -> UserAccount:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="set user session policy",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="set session policy",
        )
        user = self._auth_queries.require_user(user_id)
        previous_timeout = user.session_timeout_minutes_override
        previous_revision = user.session_revision
        user.session_timeout_minutes_override = session_timeout_minutes_override
        user.updated_at = datetime.now(UTC)
        rotate_session_revision(user)
        user.session_expires_at = next_session_expiry(user.updated_at, user=user)
        self._lifecycle.revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        with self._tx.uow() as uow:
            self._user_repo.update(user)
            self._audit.add_atomic_security_audit(
                operation="auth.session.policy.update",
                entity_type="user",
                entity_id=user.id,
                action="auth.session.policy.update",
                severity="high",
                field="session_timeout_minutes_override",
                old_value=(
                    str(previous_timeout)
                    if previous_timeout is not None
                    else None
                ),
                new_value=(
                    str(user.session_timeout_minutes_override)
                    if user.session_timeout_minutes_override is not None
                    else None
                ),
                metadata={
                    "previous_session_revision": previous_revision,
                    "session_revision": user.session_revision,
                },
            )
            uow.record_event(
                UserSessionPolicyChanged(
                    user_id=user.id,
                    tenant_id=self._tx.active_tenant_id_for_event(),
                    session_timeout_minutes_override=user.session_timeout_minutes_override,
                    occurred_at=user.updated_at,
                )
            )
            uow.commit()
        self._lifecycle.refresh_current_session_if_user(user.id)
        return user

    def revoke_user_sessions(self, user_id: str, *, note: str = "") -> UserDto:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="revoke user sessions",
        )
        self._target_users.require_target_user_in_active_tenant(
            user_id,
            operation_label="revoke sessions",
        )
        user = self._auth_queries.require_user(user_id)
        previous_revision = user.session_revision
        rotate_session_revision(user)
        user.session_expires_at = datetime.now(UTC)
        user.updated_at = user.session_expires_at
        self._lifecycle.revoke_all_persisted_sessions(user, revoked_at=user.updated_at)
        with self._tx.uow() as uow:
            self._user_repo.update(user)
            self._audit.add_atomic_security_audit(
                operation="auth.session.revoked",
                entity_type="user",
                entity_id=user.id,
                action="auth.session.revoked",
                severity="high",
                field="session_revision",
                old_value=str(previous_revision),
                new_value=str(user.session_revision),
                metadata={
                    "scope": "all",
                    "note": note.strip(),
                },
            )
            uow.record_event(
                UserSessionsRevoked(
                    user_id=user.id,
                    tenant_id=self._tx.active_tenant_id_for_event(),
                    scope="all",
                    occurred_at=user.updated_at,
                )
            )
            uow.commit()
        self._lifecycle.refresh_current_session_if_user(user.id)
        response_user = user
        return response_mapper.serialize_user(response_user, role_names=tuple(sorted(self._auth_queries.get_user_role_names(response_user.id))))

    def persist_session_context(self, session_context) -> None:
        if self._auth_session_repo is None:
            return
        principal = getattr(session_context, "principal", None)
        session_id = str(getattr(principal, "session_id", "") or "").strip() or None
        if session_id is None:
            return
        try:
            self._auth_session_repo.persist_context(
                session_id,
                last_active_tenant_id=session_context.stored_active_tenant_id(),
                last_active_organization_id=session_context.stored_active_organization_id(),
                updated_at=datetime.now(UTC),
            )
        except Exception:
            logger.exception(
                "Failed to persist auth session context session_id=%s",
                session_id,
            )

    def _touch_session_validation(self, session_id: str, *, validated_at: datetime) -> None:
        if self._auth_session_repo is None:
            return
        try:
            self._auth_session_repo.touch_validation(
                session_id,
                validated_at=validated_at,
                throttle_seconds=_SESSION_VALIDATION_THROTTLE_SECONDS,
            )
        except Exception:
            logger.exception(
                "Failed to update auth session validation heartbeat session_id=%s",
                session_id,
            )

    def revoke_session(self, session_id: str, *, note: str = "") -> AuthSession:
        require_any_permission(
            self._user_session,
            ("auth.manage", "security.manage"),
            operation_label="revoke session",
        )
        if self._auth_session_repo is None:
            raise ValidationError(
                "Session persistence is not configured.",
                code="AUTH_SESSION_PERSISTENCE_REQUIRED",
            )
        auth_session = self._auth_session_repo.get(session_id)
        if auth_session is None:
            raise ValidationError("Session not found.", code="AUTH_SESSION_NOT_FOUND")
        self._target_users.require_target_user_in_active_tenant(
            auth_session.user_id,
            operation_label="revoke session",
        )
        if auth_session.revoked_at is not None:
            self._lifecycle.refresh_current_session_if_user(auth_session.user_id)
            return auth_session
        revoked_at = datetime.now(UTC)
        previous_revoked_at = auth_session.revoked_at
        auth_session.revoked_at = revoked_at
        auth_session.updated_at = revoked_at
        with self._tx.uow() as uow:
            self._auth_session_repo.update(auth_session)
            self._audit.add_atomic_security_audit(
                operation="auth.session.revoked",
                entity_type="auth_session",
                entity_id=auth_session.id,
                action="auth.session.revoked",
                severity="high",
                field="revoked_at",
                old_value=(
                    previous_revoked_at.isoformat()
                    if previous_revoked_at is not None
                    else None
                ),
                new_value=revoked_at.isoformat(),
                metadata={
                    "scope": "single",
                    "target_user_id": auth_session.user_id,
                    "note": note.strip(),
                },
            )
            uow.commit()
        self._lifecycle.refresh_current_session_if_user(auth_session.user_id)
        return auth_session

    def validate_session_principal(self, principal: UserSessionPrincipal) -> UserSessionPrincipal | None:
        user = self._user_repo.get(principal.user_id)
        if user is None or not user.is_active:
            return None
        now = datetime.now(UTC)
        current_expires_at = ensure_utc_datetime(user.session_expires_at)
        if current_expires_at is None or now >= current_expires_at:
            return None
        principal_expires_at = ensure_utc_datetime(principal.session_expires_at)
        principal_session_id = getattr(principal, "session_id", None)
        if self._auth_session_repo is not None and principal_session_id:
            auth_session = self._auth_session_repo.get(principal_session_id)
            if auth_session is None or auth_session.user_id != user.id:
                return None
            if auth_session.revoked_at is not None:
                return None
            session_expires_at = ensure_utc_datetime(auth_session.expires_at)
            if session_expires_at is None or now >= session_expires_at:
                return None
            if int(auth_session.session_revision or 1) != int(getattr(user, "session_revision", 1) or 1):
                return None
            self._touch_session_validation(auth_session.id, validated_at=now)
            try:
                return self._principals.build(user, session_id=auth_session.id)
            except Exception:
                logger.warning(
                    "Session context revalidation denied user_id=%s session_id=%s",
                    user.id,
                    auth_session.id,
                    exc_info=True,
                )
                return None
        if principal_expires_at is None or principal_expires_at != current_expires_at:
            return None
        if int(getattr(principal, "session_revision", 1) or 1) != int(getattr(user, "session_revision", 1) or 1):
            return None
        try:
            return self._principals.build(user)
        except Exception:
            logger.warning(
                "Legacy session context revalidation denied user_id=%s",
                user.id,
                exc_info=True,
            )
            return None


__all__ = ["AuthSessionCommandHandler"]
