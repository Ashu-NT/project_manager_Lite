from __future__ import annotations

from typing import Iterable, TypeVar

from core.platform.authorization import get_authorization_engine
from core.platform.common.exceptions import BusinessRuleError
from core.platform.auth.session import UserSessionContext


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
    raise BusinessRuleError(
        (
            f"Permission denied for {operation_label}. "
            f"Missing scoped '{permission_code}' access for {normalized_scope_type} '{normalized_scope_id}'."
        ),
        code="PERMISSION_DENIED",
    )


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
    "filter_scope_rows",
    "require_project_permission",
    "require_scope_permission",
]
