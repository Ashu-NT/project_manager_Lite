from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class UserSessionPrincipal:
    user_id: str
    username: str
    display_name: str | None
    role_names: FrozenSet[str]
    permissions: FrozenSet[str]


class UserSessionContext:
    def __init__(self):
        self._principal: UserSessionPrincipal | None = None

    @property
    def principal(self) -> UserSessionPrincipal | None:
        return self._principal

    def set_principal(self, principal: UserSessionPrincipal) -> None:
        self._principal = principal

    def clear(self) -> None:
        self._principal = None

    def is_authenticated(self) -> bool:
        return self._principal is not None

    def has_permission(self, permission_code: str) -> bool:
        if self._principal is None:
            return True
        return permission_code in self._principal.permissions


__all__ = ["UserSessionPrincipal", "UserSessionContext"]

