from __future__ import annotations

from typing import Iterable, TypeVar

from src.core.platform.access.authorization import (
    filter_scope_rows,
    require_scope_permission,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    record_authorization_denial,
)
from src.core.platform.common.exceptions import BusinessRuleError

_T = TypeVar("_T")


def require_project_permission(
    user_session: UserSessionContext | None,
    project_id: str,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    require_scope_permission(
        user_session,
        "project",
        project_id,
        permission_code,
        operation_label=operation_label,
    )


def require_any_project_permission(
    user_session: UserSessionContext | None,
    project_id: str,
    permission_codes: Iterable[str],
    *,
    operation_label: str,
) -> None:
    codes = tuple(code for code in permission_codes if str(code).strip())
    if user_session is not None and any(
        user_session.has_project_permission(project_id, code) for code in codes
    ):
        return
    record_authorization_denial(
        user_session,
        operation_label=operation_label,
        reason_code="PERMISSION_DENIED",
        required_permissions=codes,
        target_scope_type="project",
        target_scope_id=project_id,
    )
    expected = " or ".join(f"'{code}'" for code in codes) or "project permission"
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing one of {expected}.",
        code="PERMISSION_DENIED",
    )


def filter_project_rows(
    rows: Iterable[_T],
    user_session: UserSessionContext | None,
    *,
    permission_code: str,
    project_id_getter,
) -> list[_T]:
    return filter_scope_rows(
        rows,
        user_session,
        scope_type="project",
        permission_code=permission_code,
        scope_id_getter=project_id_getter,
    )


__all__ = [
    "filter_project_rows",
    "require_any_project_permission",
    "require_project_permission",
]
