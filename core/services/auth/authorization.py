from __future__ import annotations

from core.exceptions import BusinessRuleError
from core.services.auth.session import UserSessionContext


def require_permission(
    user_session: UserSessionContext | None,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    if user_session is None:
        return
    if user_session.has_permission(permission_code):
        return
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing '{permission_code}'.",
        code="PERMISSION_DENIED",
    )


__all__ = ["require_permission"]

