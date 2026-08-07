from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.domain.security.auth import AuthSession
from src.core.platform.domain.security.auth.login_security_policy import (
    login_lockout_minutes,
    login_lockout_threshold,
)
from src.core.platform.common.exceptions import BusinessRuleError

from src.core.platform.application.security.auth.audit.audit_recorder import add_atomic_auth_event
from src.core.platform.application.security.auth.session.session_service import refresh_current_session_if_user
from src.core.platform.application.security.auth.session.session_utils import next_session_expiry

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth import UserAccount

    from src.core.platform.application.security.auth.auth_service import AuthService

logger = logging.getLogger(__name__)


def _current_session_context_for_user(
    service: AuthService,
    user_id: str,
) -> tuple[str | None, str | None]:
    if service._user_session is None:
        return None, None
    principal = service._user_session.principal
    if principal is None or principal.user_id != user_id:
        return None, None
    return (
        service._user_session.active_tenant_id(),
        service._user_session.active_organization_id(),
    )


def _preferred_restore_session(
    service: AuthService,
    user: UserAccount,
) -> AuthSession | None:
    if service._auth_session_repo is None:
        return None
    active_session_id = (
        str(getattr(user, "active_session_id", "") or "").strip() or None
    )
    if active_session_id is not None:
        auth_session = service._auth_session_repo.get(active_session_id)
        if auth_session is not None:
            return auth_session
    sessions = service._auth_session_repo.list_by_user(user.id)
    for auth_session in sessions:
        if auth_session.revoked_at is None:
            return auth_session
    return sessions[0] if sessions else None


def _resolve_last_active_context(
    service: AuthService,
    user: UserAccount,
) -> tuple[str | None, str | None]:
    active_tenant_id, active_organization_id = (
        _current_session_context_for_user(service, user.id)
    )
    if active_tenant_id is None and active_organization_id is None:
        restore_session = _preferred_restore_session(service, user)
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

    candidates: list[tuple[str | None, str | None]] = []
    if active_tenant_id is not None or active_organization_id is not None:
        candidates.append((active_tenant_id, active_organization_id))
    if service._tenant_context_service is not None:
        initial_tenant_id = (
            service._tenant_context_service.initial_tenant_id_for_user(user.id)
        )
        initial_organization_id = (
            service._tenant_context_service.initial_organization_id_for_tenant(
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
            principal = service.build_principal_for_context(
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
    service: AuthService,
    *,
    username: str,
    user: UserAccount | None,
    reason: str,
    details: dict[str, object] | None = None,
) -> None:
    try:
        tenant_id, organization_id = (
            _resolve_last_active_context(service, user)
            if user is not None
            else (None, None)
        )
        add_atomic_auth_event(
            service,
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
        service._session.commit()
    except Exception:
        service._session.rollback()
        logger.exception(
            "Authentication denial audit persistence failed reason=%s user_id=%s",
            reason,
            user.id if user is not None else None,
        )


def complete_successful_authentication(
    service: AuthService,
    user: UserAccount,
    *,
    occurred_at: datetime,
    auth_method: str,
    device_label: str | None,
) -> None:
    try:
        last_active_tenant_id, last_active_organization_id = (
            _resolve_last_active_context(service, user)
        )
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = occurred_at
        user.last_login_auth_method = auth_method
        user.last_login_device_label = device_label
        user.session_expires_at = next_session_expiry(occurred_at, user=user)
        user.updated_at = occurred_at
        if service._auth_session_repo is not None:
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
            service._auth_session_repo.add(auth_session)
        else:
            user.active_session_id = None
        service._user_repo.update(user)
        add_atomic_auth_event(
            service,
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
        service._session.commit()
    except Exception as exc:
        service._session.rollback()
        logger.exception(
            "Successful authentication rolled back because audit persistence "
            "failed user_id=%s",
            user.id,
        )
        raise BusinessRuleError(
            "Authentication could not be completed securely. Please try again.",
            code="AUTH_AUDIT_UNAVAILABLE",
        ) from exc
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


def register_failed_login(
    service: AuthService,
    user: UserAccount,
    *,
    username: str,
    occurred_at: datetime,
    reason: str = "invalid_credentials",
    auth_method: str = "password",
) -> None:
    try:
        tenant_id, organization_id = _resolve_last_active_context(service, user)
        user.failed_login_attempts = (
            int(getattr(user, "failed_login_attempts", 0) or 0) + 1
        )
        if user.failed_login_attempts >= login_lockout_threshold():
            user.locked_until = occurred_at + timedelta(
                minutes=login_lockout_minutes()
            )
        user.updated_at = occurred_at
        service._user_repo.update(user)
        add_atomic_auth_event(
            service,
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
        service._session.commit()
    except Exception:
        service._session.rollback()
        logger.exception(
            "Authentication failure state and audit persistence rolled back "
            "user_id=%s reason=%s",
            user.id,
            reason,
        )
        return
    domain_events.auth_changed.emit(user.id)
    if user.locked_until is not None:
        logger.warning(
            "User '%s' locked out until %s after %s failed attempts.",
            username,
            user.locked_until.isoformat(),
            user.failed_login_attempts,
        )


__all__ = [
    "complete_successful_authentication",
    "persist_standalone_login_denial",
    "register_failed_login",
]
