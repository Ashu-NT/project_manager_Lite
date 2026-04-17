from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, TypeVar

from src.core.platform.authorization.domain import AuthorizationEngine

if TYPE_CHECKING:
    from src.core.platform.auth.domain.session import UserSessionContext


_T = TypeVar("_T")


class SessionAuthorizationEngine:
    """Default authorization engine backed by the current session principal.

    The optional ``resource`` / ``context`` parameters are reserved for future
    policy enrichment so desktop and web callers can move toward ABAC-style
    decisions without changing every callsite again.
    """

    def has_permission(
        self,
        user_session: UserSessionContext | None,
        permission_code: str,
        *,
        resource: object | None = None,
        context: dict[str, object] | None = None,
    ) -> bool:
        del resource, context
        return bool(user_session is not None and user_session.has_permission(permission_code))

    def has_any_permission(
        self,
        user_session: UserSessionContext | None,
        permission_codes: Iterable[str],
        *,
        resource: object | None = None,
        context: dict[str, object] | None = None,
    ) -> bool:
        del resource, context
        return bool(
            user_session is not None
            and any(user_session.has_permission(code) for code in permission_codes if str(code).strip())
        )

    def is_admin_session(self, user_session: UserSessionContext | None) -> bool:
        principal = user_session.principal if user_session is not None else None
        return bool(principal is not None and "admin" in principal.role_names)

    def has_scope_permission(
        self,
        user_session: UserSessionContext | None,
        scope_type: str,
        scope_id: str,
        permission_code: str,
        *,
        resource: object | None = None,
        context: dict[str, object] | None = None,
    ) -> bool:
        del resource, context
        return bool(
            user_session is not None
            and user_session.has_scope_permission(scope_type, scope_id, permission_code)
        )

    def scope_ids_for(
        self,
        user_session: UserSessionContext | None,
        scope_type: str,
        permission_code: str,
        *,
        resource: object | None = None,
        context: dict[str, object] | None = None,
    ) -> set[str]:
        del resource, context
        if user_session is None:
            return set()
        return user_session.scope_ids_for(scope_type, permission_code)

    def is_scope_restricted(
        self,
        user_session: UserSessionContext | None,
        scope_type: str,
        *,
        resource: object | None = None,
        context: dict[str, object] | None = None,
    ) -> bool:
        del resource, context
        if user_session is None:
            return False
        return user_session.is_scope_restricted(scope_type)

    def filter_scope_rows(
        self,
        rows: Iterable[_T],
        user_session: UserSessionContext | None,
        *,
        scope_type: str,
        permission_code: str,
        scope_id_getter: Callable[[_T], str],
        resource_type: str | None = None,
        context: dict[str, object] | None = None,
    ) -> list[_T]:
        del resource_type, context
        if not self.has_permission(user_session, permission_code):
            return []
        materialized_rows = list(rows)
        if not self.is_scope_restricted(user_session, scope_type):
            return materialized_rows
        allowed_ids = self.scope_ids_for(user_session, scope_type, permission_code)
        return [row for row in materialized_rows if scope_id_getter(row) in allowed_ids]


_authorization_engine: AuthorizationEngine = SessionAuthorizationEngine()


def get_authorization_engine() -> AuthorizationEngine:
    return _authorization_engine


def set_authorization_engine(engine: AuthorizationEngine | None) -> None:
    global _authorization_engine
    _authorization_engine = engine or SessionAuthorizationEngine()


__all__ = [
    "SessionAuthorizationEngine",
    "get_authorization_engine",
    "set_authorization_engine",
]
