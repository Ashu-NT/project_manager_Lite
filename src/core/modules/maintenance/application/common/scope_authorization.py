from __future__ import annotations

from typing import NoReturn

from src.core.platform.application.security.authorization.enforcement.permission_checks import authorization_denied
from src.core.platform.domain.security.auth import UserSessionContext


def deny_maintenance_scope_access(
    user_session: UserSessionContext | None,
    *,
    operation_label: str,
    message: str,
) -> NoReturn:
    """Deny a maintenance resource that cannot be matched to a scope grant."""
    authorization_denied(
        user_session,
        message=message,
        code="PERMISSION_DENIED",
        operation_label=operation_label,
        target_scope_type="maintenance",
        operation="authorization.resource_scope.denied",
    )


__all__ = ["deny_maintenance_scope_access"]
