from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.core.platform.application.security.auth.session.session_utils import (
    next_session_expiry,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.core.platform.domain.security.auth import AuthSession
from src.core.platform.domain.security.auth.events import (
    AccountLocked,
    AccountUnlocked,
    AuthenticationFailureRecorded,
)
from src.core.platform.domain.security.auth.login_security_policy import (
    login_lockout_minutes,
    login_lockout_threshold,
)

logger = logging.getLogger(__name__)
from src.core.platform.application.security.auth.audit.security_audit import (
    SecurityAuditRecorder,
)
from src.core.platform.application.security.auth.auth_transaction_scope import (
    AuthTransactionScope,
)
from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.contract.repositories.security.auth import (
    AuthSessionRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount


class AuthenticationTransactions:
    """Login outcome transactions: persist a successful login's session and
    context, failed-attempt lockout, and standalone denial audit."""

    def __init__(
        self,
        *,
        tx: AuthTransactionScope,
        user_repo: UserRepository,
        auth_session_repo: AuthSessionRepository | None,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
        principals: PrincipalBuilder,
        lifecycle: AuthSessionLifecycle,
        audit: SecurityAuditRecorder,
    ) -> None:
        self._tx = tx
        self._user_repo = user_repo
        self._auth_session_repo = auth_session_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        self._principals = principals
        self._lifecycle = lifecycle
        self._audit = audit

    def _current_session_context_for_user(
        self,
        user_id: str,
    ) -> tuple[str | None, str | None]:
        if self._user_session is None:
            return None, None
        principal = self._user_session.principal
        if principal is None or principal.user_id != user_id:
            return None, None
        return (
            self._user_session.active_tenant_id(),
            self._user_session.active_organization_id(),
        )

    def _preferred_restore_session(
        self,
        user: UserAccount,
    ) -> AuthSession | None:
        if self._auth_session_repo is None:
            return None
        active_session_id = (
            str(getattr(user, "active_session_id", "") or "").strip() or None
        )
        if active_session_id is not None:
            auth_session = self._auth_session_repo.get(active_session_id)
            if auth_session is not None:
                return auth_session
        sessions = self._auth_session_repo.list_by_user(user.id)
        for auth_session in sessions:
            if auth_session.revoked_at is None:
                return auth_session
        return sessions[0] if sessions else None

    def _resolve_last_active_context(
        self,
        user: UserAccount,
    ) -> tuple[str | None, str | None]:
        active_tenant_id, active_organization_id = (
            self._current_session_context_for_user(user.id)
        )
        if active_tenant_id is None and active_organization_id is None:
            restore_session = self._preferred_restore_session(user)
            if restore_session is not None:
                active_tenant_id = (
                    str(
                        getattr(
                            restore_session,
                            "last_active_tenant_id",
                            "",
                        )
                        or ""
                    ).strip()
                    or None
                )
                active_organization_id = (
                    str(
                        getattr(
                            restore_session,
                            "last_active_organization_id",
                            "",
                        )
                        or ""
                    ).strip()
                    or None
                )

        # A tenant was restored (current session or persisted) but no organization
        # was -- apply the same sole-enabled-organization auto-select a brand-new
        # login already gets, rather than leaving this candidate stuck at a
        # tenant-only context forever. Without this, a session once persisted with
        # organization_id=None (e.g. an organization that briefly became
        # inaccessible) permanently shadows the correct auto-select on every later
        # login: the tenant-only candidate below still succeeds (organization is
        # optional at principal-build time), so the real auto-select candidate is
        # never reached.
        if (
            active_tenant_id is not None
            and active_organization_id is None
            and self._tenant_context_service is not None
        ):
            active_organization_id = (
                self._tenant_context_service.initial_organization_id_for_tenant(
                    active_tenant_id
                )
            )

        candidates: list[tuple[str | None, str | None]] = []
        if active_tenant_id is not None or active_organization_id is not None:
            candidates.append((active_tenant_id, active_organization_id))
        if self._tenant_context_service is not None:
            initial_tenant_id = (
                self._tenant_context_service.initial_tenant_id_for_user(user.id)
            )
            initial_organization_id = (
                self._tenant_context_service.initial_organization_id_for_tenant(
                    initial_tenant_id
                )
                if initial_tenant_id is not None
                else None
            )
            initial_context = (initial_tenant_id, initial_organization_id)
            if initial_context not in candidates:
                candidates.append(initial_context)
        candidates.append((None, None))

        for tenant_id, organization_id in candidates:
            try:
                principal = self._principals.build_for_context(
                    user,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    session_id=None,
                )
            except Exception:
                logger.warning(
                    "Rejected saved authentication context user_id=%s tenant_id=%s "
                    "organization_id=%s",
                    user.id,
                    tenant_id,
                    organization_id,
                    exc_info=True,
                )
                continue
            return principal.active_tenant_id, principal.active_organization_id
        return None, None

    def persist_standalone_login_denial(
        self,
        *,
        username: str,
        user: UserAccount | None,
        reason: str,
        details: dict[str, object] | None = None,
    ) -> None:
        try:
            tenant_id, organization_id = (
                self._resolve_last_active_context(user)
                if user is not None
                else (None, None)
            )
            self._audit.add_atomic_auth_event(
                action="auth.login.failed",
                username=username,
                user_id=user.id if user is not None else None,
                outcome="denied",
                tenant_id=tenant_id,
                organization_id=organization_id,
                details={
                    **dict(details or {}),
                    "reason": reason,
                },
            )
            self._tx.session.commit()
        except Exception:
            self._tx.session.rollback()
            logger.exception(
                "Authentication denial audit persistence failed reason=%s user_id=%s",
                reason,
                user.id if user is not None else None,
            )

    def complete_successful_authentication(
        self,
        user: UserAccount,
        *,
        occurred_at: datetime,
        auth_method: str,
        device_label: str | None,
    ) -> None:
        previous_failed_attempts = user.failed_login_attempts
        previous_locked_until = user.locked_until
        try:
            last_active_tenant_id, last_active_organization_id = (
                self._resolve_last_active_context(user)
            )
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = occurred_at
            user.last_login_auth_method = auth_method
            user.last_login_device_label = device_label
            user.session_expires_at = next_session_expiry(occurred_at, user=user)
            user.updated_at = occurred_at
            if self._auth_session_repo is not None:
                auth_session = AuthSession.create(
                    user_id=user.id,
                    session_revision=getattr(user, "session_revision", 1),
                    auth_method=auth_method,
                    expires_at=user.session_expires_at,
                    device_label=user.last_login_device_label,
                    last_active_tenant_id=last_active_tenant_id,
                    last_active_organization_id=last_active_organization_id,
                )
                user.active_session_id = auth_session.id
                self._auth_session_repo.add(auth_session)
            else:
                user.active_session_id = None
            with self._tx.uow() as uow:
                self._user_repo.update(user)
                self._audit.add_atomic_auth_event(
                    action="auth.login.success",
                    username=user.username,
                    user_id=user.id,
                    outcome="success",
                    tenant_id=last_active_tenant_id,
                    organization_id=last_active_organization_id,
                    entity_id=user.active_session_id,
                    details={
                        "result": "ok",
                        "auth_method": auth_method,
                        "identity_provider": str(
                            getattr(user, "identity_provider", "") or ""
                        ),
                        "device_label": str(
                            getattr(user, "last_login_device_label", "") or ""
                        ),
                        "session_expires_at": (
                            user.session_expires_at.isoformat()
                            if user.session_expires_at
                            else ""
                        ),
                        "target_user_id": user.id,
                    },
                )
                if previous_failed_attempts > 0 or previous_locked_until is not None:
                    uow.record_event(
                        AccountUnlocked(
                            user_id=user.id,
                            tenant_id=last_active_tenant_id,
                            occurred_at=occurred_at,
                        )
                    )
                uow.commit()
        except Exception as exc:
            logger.exception(
                "Successful authentication rolled back because audit persistence "
                "failed user_id=%s",
                user.id,
            )
            raise BusinessRuleError(
                "Authentication could not be completed securely. Please try again.",
                code="AUTH_AUDIT_UNAVAILABLE",
            ) from exc
        self._lifecycle.refresh_current_session_if_user(user.id)

    def register_failed_login(
        self,
        user: UserAccount,
        *,
        username: str,
        occurred_at: datetime,
        reason: str = "invalid_credentials",
        auth_method: str = "password",
    ) -> None:
        """Records this failed attempt against the account's durable lockout state, atomically
        with its own required audit entry. Two concurrent failed logins against the same account
        race on `UserAccount`'s real CAS (`update_with_version_check`); the loser gets exactly one
        bounded retry -- reload the latest state, reapply this attempt's increment, retry the
        commit once. Any other failure propagates -- never silently discarded."""
        tenant_id, organization_id = self._resolve_last_active_context(user)
        max_attempts = 2
        for attempt_number in range(1, max_attempts + 1):
            if attempt_number > 1:
                reloaded = self._user_repo.get(user.id)
                if reloaded is None:
                    raise BusinessRuleError(
                        "The account no longer exists.",
                        code="AUTH_USER_NOT_FOUND",
                    )
                user = reloaded
            previous_failed_attempts = int(getattr(user, "failed_login_attempts", 0) or 0)
            user.failed_login_attempts = previous_failed_attempts + 1
            threshold = login_lockout_threshold()
            crosses_threshold = (
                previous_failed_attempts < threshold
                and user.failed_login_attempts >= threshold
            )
            if user.failed_login_attempts >= threshold:
                user.locked_until = occurred_at + timedelta(
                    minutes=login_lockout_minutes()
                )
            user.updated_at = occurred_at
            try:
                with self._tx.uow() as uow:
                    self._user_repo.update(user)
                    self._audit.add_atomic_auth_event(
                        action="auth.login.failed",
                        username=username,
                        user_id=user.id,
                        outcome="denied",
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        details={
                            "reason": reason,
                            "auth_method": auth_method,
                            "failed_attempts": user.failed_login_attempts,
                            "locked_until": (
                                user.locked_until.isoformat()
                                if user.locked_until is not None
                                else ""
                            ),
                        },
                    )
                    if crosses_threshold and user.locked_until is not None:
                        uow.record_event(
                            AccountLocked(
                                user_id=user.id,
                                tenant_id=tenant_id,
                                locked_until=user.locked_until,
                                failed_attempts=user.failed_login_attempts,
                                occurred_at=occurred_at,
                            )
                        )
                    else:
                        uow.record_event(
                            AuthenticationFailureRecorded(
                                user_id=user.id,
                                tenant_id=tenant_id,
                                failed_attempts=user.failed_login_attempts,
                                occurred_at=occurred_at,
                            )
                        )
                    uow.commit()
                break
            except ConcurrencyError:
                if attempt_number >= max_attempts:
                    logger.exception(
                        "Authentication failure state could not be persisted after a "
                        "concurrent-write retry user_id=%s reason=%s",
                        user.id,
                        reason,
                    )
                    raise
                logger.info(
                    "Authentication failure state retrying after a concurrent write "
                    "user_id=%s reason=%s",
                    user.id,
                    reason,
                )
                continue
        if user.locked_until is not None:
            logger.warning(
                "User '%s' locked out until %s after %s failed attempts.",
                username,
                user.locked_until.isoformat(),
                user.failed_login_attempts,
            )


__all__ = ["AuthenticationTransactions"]
