from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_any_permission
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain import AuthSession
from src.core.platform.auth.domain.session import UserSessionPrincipal
from src.core.platform.common.exceptions import ValidationError

from .audit_recorder import record_auth_event
from .principal_builder import build_principal
from .session_utils import next_session_expiry, rotate_session_revision, validate_session_timeout_override

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService

logger = logging.getLogger(__name__)
_SESSION_VALIDATION_THROTTLE_SECONDS = 60


def revoke_all_persisted_sessions(service: AuthService, user: UserAccount, *, revoked_at: datetime) -> None:
    if service._auth_session_repo is None:
        return
    for auth_session in service._auth_session_repo.list_by_user(user.id):
        if auth_session.revoked_at is not None:
            continue
        auth_session.revoked_at = revoked_at
        auth_session.updated_at = revoked_at
        service._auth_session_repo.update(auth_session)


def resolve_current_principal_session_id(service: AuthService, user_id: str) -> str | None:
    if service._user_session is None:
        return None
    principal = service._user_session.principal
    if principal is None or principal.user_id != user_id:
        return None
    session_id = str(getattr(principal, "session_id", "") or "").strip() or None
    if session_id is None or service._auth_session_repo is None:
        return session_id
    auth_session = service._auth_session_repo.get(session_id)
    if auth_session is None or auth_session.revoked_at is not None:
        return None
    return session_id


def refresh_current_session_if_user(service: AuthService, user_id: str) -> None:
    if service._user_session is None:
        return
    principal = service._user_session.principal
    if principal is None or principal.user_id != user_id:
        return
    user = service._user_repo.get(user_id)
    if user is None or not user.is_active:
        service._user_session.clear()
        return
    if user.session_expires_at is not None and datetime.now(timezone.utc) >= ensure_utc_datetime(user.session_expires_at):
        service._user_session.clear()
        return
    preferred_session_id = resolve_current_principal_session_id(service, user_id)
    service._user_session.set_principal(build_principal(service, user, session_id=preferred_session_id))


def set_user_session_policy(
    service: AuthService,
    user_id: str,
    *,
    session_timeout_minutes_override: int | None,
) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="set user session policy",
    )
    user = service._require_user(user_id)
    user.session_timeout_minutes_override = validate_session_timeout_override(session_timeout_minutes_override)
    user.updated_at = datetime.now(timezone.utc)
    rotate_session_revision(user)
    user.session_expires_at = next_session_expiry(user.updated_at, user=user)
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def revoke_user_sessions(service: AuthService, user_id: str, *, note: str = "") -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="revoke user sessions",
    )
    user = service._require_user(user_id)
    rotate_session_revision(user)
    user.session_expires_at = datetime.now(timezone.utc)
    user.updated_at = user.session_expires_at
    revoke_all_persisted_sessions(service, user, revoked_at=user.updated_at)
    service._user_repo.update(user)
    service._session.commit()
    domain_events.auth_changed.emit(user.id)
    record_auth_event(
        service,
        action="auth.session.revoked",
        username=user.username,
        user_id=user.id,
        details={"note": note.strip()},
    )
    refresh_current_session_if_user(service, user.id)
    return user


def list_user_sessions(service: AuthService, user_id: str) -> list[AuthSession]:
    require_any_permission(
        service._user_session,
        ("auth.read", "auth.manage", "security.manage"),
        operation_label="list user sessions",
    )
    user = service._require_user(user_id)
    if service._auth_session_repo is None:
        return []
    return service._auth_session_repo.list_by_user(user.id)


def persist_session_context(service: AuthService, session_context) -> None:
    if service._auth_session_repo is None:
        return
    principal = getattr(session_context, "principal", None)
    session_id = str(getattr(principal, "session_id", "") or "").strip() or None
    if session_id is None:
        return
    try:
        service._auth_session_repo.persist_context(
            session_id,
            last_active_tenant_id=session_context.active_tenant_id(),
            last_active_organization_id=session_context.active_organization_id(),
            updated_at=datetime.now(timezone.utc),
        )
    except Exception:
        logger.exception(
            "Failed to persist auth session context session_id=%s",
            session_id,
        )


def _touch_session_validation(service: AuthService, session_id: str, *, validated_at: datetime) -> None:
    if service._auth_session_repo is None:
        return
    try:
        service._auth_session_repo.touch_validation(
            session_id,
            validated_at=validated_at,
            throttle_seconds=_SESSION_VALIDATION_THROTTLE_SECONDS,
        )
    except Exception:
        logger.exception(
            "Failed to update auth session validation heartbeat session_id=%s",
            session_id,
        )


def revoke_session(service: AuthService, session_id: str, *, note: str = "") -> AuthSession:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="revoke session",
    )
    if service._auth_session_repo is None:
        raise ValidationError(
            "Session persistence is not configured.",
            code="AUTH_SESSION_PERSISTENCE_REQUIRED",
        )
    auth_session = service._auth_session_repo.get(session_id)
    if auth_session is None:
        raise ValidationError("Session not found.", code="AUTH_SESSION_NOT_FOUND")
    revoked_at = datetime.now(timezone.utc)
    auth_session.revoked_at = revoked_at
    auth_session.updated_at = revoked_at
    service._auth_session_repo.update(auth_session)
    service._session.commit()
    record_auth_event(
        service,
        action="auth.session.revoked",
        username="",
        user_id=auth_session.user_id,
        details={"note": note.strip(), "session_id": auth_session.id},
    )
    refresh_current_session_if_user(service, auth_session.user_id)
    return auth_session


def validate_session_principal(service: AuthService, principal: UserSessionPrincipal) -> UserSessionPrincipal | None:
    user = service._user_repo.get(principal.user_id)
    if user is None or not user.is_active:
        return None
    now = datetime.now(timezone.utc)
    current_expires_at = ensure_utc_datetime(user.session_expires_at)
    if current_expires_at is None or now >= current_expires_at:
        return None
    principal_expires_at = ensure_utc_datetime(principal.session_expires_at)
    if service._auth_session_repo is not None and getattr(principal, "session_id", None):
        auth_session = service._auth_session_repo.get(principal.session_id)
        if auth_session is None or auth_session.user_id != user.id:
            return None
        if auth_session.revoked_at is not None:
            return None
        if auth_session.expires_at is None or now >= ensure_utc_datetime(auth_session.expires_at):
            return None
        if int(auth_session.session_revision or 1) != int(getattr(user, "session_revision", 1) or 1):
            return None
        _touch_session_validation(service, auth_session.id, validated_at=now)
        if principal_expires_at is None or principal_expires_at != ensure_utc_datetime(auth_session.expires_at):
            return build_principal(service, user, session_id=auth_session.id)
        return build_principal(service, user, session_id=auth_session.id)
    if principal_expires_at is None or principal_expires_at != current_expires_at:
        return None
    if int(getattr(principal, "session_revision", 1) or 1) != int(getattr(user, "session_revision", 1) or 1):
        return None
    return build_principal(service, user)


__all__ = [
    "list_user_sessions",
    "persist_session_context",
    "refresh_current_session_if_user",
    "resolve_current_principal_session_id",
    "revoke_all_persisted_sessions",
    "revoke_session",
    "revoke_user_sessions",
    "set_user_session_policy",
    "validate_session_principal",
]
