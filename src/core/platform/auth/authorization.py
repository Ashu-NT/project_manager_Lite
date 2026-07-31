from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import NoReturn

from src.core.platform.authorization import get_authorization_engine
from src.core.platform.authorization.domain import SecurityDenialEvent
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.auth.domain.session import UserSessionContext

logger = logging.getLogger(__name__)


def require_permission(
    user_session: UserSessionContext | None,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    engine = get_authorization_engine()
    if engine.has_permission(user_session, permission_code):
        return
    record_authorization_denial(
        user_session,
        operation_label=operation_label,
        reason_code="PERMISSION_DENIED",
        required_permissions=(permission_code,),
    )
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing '{permission_code}'.",
        code="PERMISSION_DENIED",
    )


def require_any_permission(
    user_session: UserSessionContext | None,
    permission_codes: Iterable[str],
    *,
    operation_label: str,
) -> None:
    codes = [code for code in permission_codes if str(code).strip()]
    engine = get_authorization_engine()
    if engine.has_any_permission(user_session, codes):
        return
    record_authorization_denial(
        user_session,
        operation_label=operation_label,
        reason_code="PERMISSION_DENIED",
        required_permissions=codes,
    )
    expected = " or ".join(f"'{code}'" for code in codes) or "required permission"
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing one of {expected}.",
        code="PERMISSION_DENIED",
    )


def is_admin_session(user_session: UserSessionContext | None) -> bool:
    return get_authorization_engine().is_admin_session(user_session)


def record_authorization_denial(
    user_session: UserSessionContext | None,
    *,
    operation_label: str,
    reason_code: str,
    required_permissions: Iterable[str] = (),
    target_scope_type: str | None = None,
    target_scope_id: str | None = None,
    operation: str = "authorization.denied",
) -> None:
    if user_session is None:
        return
    denial_recorder = getattr(user_session, "record_security_denial", None)
    if not callable(denial_recorder):
        return
    principal = getattr(user_session, "principal", None)
    event = SecurityDenialEvent(
        operation=_clean_text(operation, fallback="authorization.denied"),
        reason_code=_clean_text(reason_code, fallback="PERMISSION_DENIED"),
        operation_label=_clean_text(operation_label, fallback="protected operation"),
        actor_user_id=(
            _clean_optional(getattr(principal, "user_id", None))
            if principal is not None
            else None
        ),
        actor_username=(
            _clean_optional(getattr(principal, "username", None))
            if principal is not None
            else None
        ),
        session_id=(
            _clean_optional(getattr(principal, "session_id", None))
            if principal is not None
            else None
        ),
        tenant_id=_stored_context_id(user_session, "stored_active_tenant_id"),
        organization_id=_stored_context_id(
            user_session,
            "stored_active_organization_id",
        ),
        required_permissions=tuple(
            sorted(
                {
                    str(permission or "").strip()
                    for permission in required_permissions
                    if str(permission or "").strip()
                }
            )
        ),
        target_scope_type=_clean_optional(target_scope_type),
        target_scope_id=_clean_optional(target_scope_id),
    )
    try:
        recorded = denial_recorder(event)
        if recorded is False:
            logger.critical(
                "Security denial audit recorder is not configured "
                "operation=%s reason_code=%s actor_user_id=%s tenant_id=%s",
                event.operation,
                event.reason_code,
                event.actor_user_id,
                event.tenant_id,
            )
    except Exception:
        logger.critical(
            "Security denial audit persistence failed operation=%s "
            "reason_code=%s actor_user_id=%s tenant_id=%s",
            event.operation,
            event.reason_code,
            event.actor_user_id,
            event.tenant_id,
            exc_info=True,
        )


def authorization_denied(
    user_session: UserSessionContext | None,
    *,
    message: str,
    code: str,
    operation_label: str,
    required_permissions: Iterable[str] = (),
    target_scope_type: str | None = None,
    target_scope_id: str | None = None,
    operation: str = "authorization.denied",
) -> NoReturn:
    """Record a post-gate authorization decision and preserve its domain error."""
    record_authorization_denial(
        user_session,
        operation_label=operation_label,
        reason_code=code,
        required_permissions=required_permissions,
        target_scope_type=target_scope_type,
        target_scope_id=target_scope_id,
        operation=operation,
    )
    raise BusinessRuleError(message, code=code)


def _clean_text(value: object, *, fallback: str) -> str:
    return str(value or "").strip()[:255] or fallback


def _clean_optional(value: object) -> str | None:
    return str(value or "").strip()[:255] or None


def _stored_context_id(
    user_session: object,
    accessor_name: str,
) -> str | None:
    accessor = getattr(user_session, accessor_name, None)
    if not callable(accessor):
        return None
    try:
        return _clean_optional(accessor())
    except Exception:
        return None


__all__ = [
    "authorization_denied",
    "is_admin_session",
    "record_authorization_denial",
    "require_any_permission",
    "require_permission",
]
