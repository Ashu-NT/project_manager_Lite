from __future__ import annotations

from typing import Iterable, TypeVar

from core.platform.common.exceptions import BusinessRuleError
from core.platform.auth.session import UserSessionContext


_T = TypeVar("_T")


def require_project_permission(
    user_session: UserSessionContext | None,
    project_id: str,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    if user_session is not None and user_session.has_project_permission(project_id, permission_code):
        return
    raise BusinessRuleError(
        (
            f"Permission denied for {operation_label}. "
            f"Missing scoped '{permission_code}' access for project '{project_id}'."
        ),
        code="PERMISSION_DENIED",
    )


def filter_project_rows(
    rows: Iterable[_T],
    user_session: UserSessionContext | None,
    *,
    permission_code: str,
    project_id_getter,
) -> list[_T]:
    if user_session is None:
        return []
    if not user_session.has_permission(permission_code):
        return []
    if not user_session.is_project_restricted():
        return list(rows)
    allowed_ids = user_session.project_ids_for(permission_code)
    return [row for row in rows if project_id_getter(row) in allowed_ids]


__all__ = ["filter_project_rows", "require_project_permission"]
