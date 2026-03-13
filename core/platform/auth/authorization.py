from __future__ import annotations

from collections.abc import Iterable

from core.platform.common.exceptions import BusinessRuleError
from core.platform.auth.session import UserSessionContext


def require_permission(
    user_session: UserSessionContext | None,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    if user_session is not None and user_session.has_permission(permission_code):
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
    if user_session is not None and any(user_session.has_permission(code) for code in codes):
        return
    expected = " or ".join(f"'{code}'" for code in codes) or "required permission"
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing one of {expected}.",
        code="PERMISSION_DENIED",
    )


def is_admin_session(user_session: UserSessionContext | None) -> bool:
    principal = user_session.principal if user_session is not None else None
    if principal is None:
        return False
    return "admin" in principal.role_names


__all__ = ["require_permission", "require_any_permission", "is_admin_session"]
