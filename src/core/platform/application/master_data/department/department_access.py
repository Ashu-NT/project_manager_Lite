from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
)

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionContext


def require_department_read_access(user_session: UserSessionContext | None, operation_label: str) -> None:
    require_any_permission(
        user_session,
        ("settings.manage", "department.read"),
        operation_label=operation_label,
    )


__all__ = ["require_department_read_access"]
