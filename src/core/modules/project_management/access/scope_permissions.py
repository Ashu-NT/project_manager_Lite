from __future__ import annotations

from typing import Iterable, TypeVar

from src.core.platform.access.authorization import (
    filter_scope_rows,
    require_scope_permission,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

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
    "require_project_permission",
]
