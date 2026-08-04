from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from src.core.platform.auth.domain.session import UserSessionContext


_T = TypeVar("_T")


class AuthorizationEngine(Protocol):
    def has_permission(
        self,
        user_session: UserSessionContext | None,
        permission_code: str,
        *,
        resource: object | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool: ...

    def has_any_permission(
        self,
        user_session: UserSessionContext | None,
        permission_codes: Iterable[str],
        *,
        resource: object | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool: ...

    def is_admin_session(self, user_session: UserSessionContext | None) -> bool: ...

    def has_scope_permission(
        self,
        user_session: UserSessionContext | None,
        scope_type: str,
        scope_id: str,
        permission_code: str,
        *,
        resource: object | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool: ...

    def scope_ids_for(
        self,
        user_session: UserSessionContext | None,
        scope_type: str,
        permission_code: str,
        *,
        resource: object | None = None,
        context: dict[str, Any] | None = None,
    ) -> set[str]: ...

    def is_scope_restricted(
        self,
        user_session: UserSessionContext | None,
        scope_type: str,
        *,
        resource: object | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool: ...

    def filter_scope_rows(
        self,
        rows: Iterable[_T],
        user_session: UserSessionContext | None,
        *,
        scope_type: str,
        permission_code: str,
        scope_id_getter: Callable[[_T], str],
        resource_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[_T]: ...


__all__ = ["AuthorizationEngine"]
