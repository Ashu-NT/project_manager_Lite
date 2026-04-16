from __future__ import annotations

from collections.abc import Iterable

from core.platform.authorization import get_authorization_engine
from core.platform.common.exceptions import BusinessRuleError
from src.core.platform.auth.domain.session import UserSessionContext


def require_permission(
    user_session: UserSessionContext | None,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    engine = get_authorization_engine()
    if engine.has_permission(user_session, permission_code):
        return
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
    expected = " or ".join(f"'{code}'" for code in codes) or "required permission"
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing one of {expected}.",
        code="PERMISSION_DENIED",
    )


def is_admin_session(user_session: UserSessionContext | None) -> bool:
    return get_authorization_engine().is_admin_session(user_session)


__all__ = ["require_permission", "require_any_permission", "is_admin_session"]
