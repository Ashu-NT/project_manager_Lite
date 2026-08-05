from __future__ import annotations

from typing import Iterable, TypeVar

from src.core.platform.application.security.authorization.enforcement.permission_checks import record_authorization_denial
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.application.security.authorization import get_authorization_engine


_T = TypeVar("_T")


def require_scope_permission(
    user_session: UserSessionContext | None,
    scope_type: str,
    scope_id: str,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    engine = get_authorization_engine()
    if engine.has_scope_permission(user_session, scope_type, scope_id, permission_code):
        return
    normalized_scope_type = str(scope_type or "").strip().lower() or "scope"
    normalized_scope_id = str(scope_id or "").strip() or "unknown"
    record_authorization_denial(
        user_session,
        operation_label=operation_label,
        reason_code="PERMISSION_DENIED",
        required_permissions=(permission_code,),
        target_scope_type=normalized_scope_type,
        target_scope_id=normalized_scope_id,
        operation="authorization.scope.denied",
    )
    raise BusinessRuleError(
        (
            f"Permission denied for {operation_label}. "
            f"Missing scoped '{permission_code}' access for {normalized_scope_type} '{normalized_scope_id}'."
        ),
        code="PERMISSION_DENIED",
    )


def filter_scope_rows(
    rows: Iterable[_T],
    user_session: UserSessionContext | None,
    *,
    scope_type: str,
    permission_code: str,
    scope_id_getter,
) -> list[_T]:
    return get_authorization_engine().filter_scope_rows(
        rows,
        user_session,
        scope_type=scope_type,
        permission_code=permission_code,
        scope_id_getter=scope_id_getter,
    )


__all__ = [
    "filter_scope_rows",
    "require_scope_permission",
]
