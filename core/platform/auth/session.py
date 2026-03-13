from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import FrozenSet

from core.platform.auth.datetime_utils import ensure_utc_datetime


@dataclass(frozen=True)
class UserSessionPrincipal:
    user_id: str
    username: str
    display_name: str | None
    role_names: FrozenSet[str]
    permissions: FrozenSet[str]
    project_access: dict[str, FrozenSet[str]] = field(default_factory=dict)
    session_expires_at: datetime | None = None


class UserSessionContext:
    def __init__(self):
        self._principal: UserSessionPrincipal | None = None

    @property
    def principal(self) -> UserSessionPrincipal | None:
        return self._principal

    def set_principal(self, principal: UserSessionPrincipal) -> None:
        self._principal = replace(
            principal,
            session_expires_at=ensure_utc_datetime(principal.session_expires_at),
        )

    def clear(self) -> None:
        self._principal = None

    def is_authenticated(self) -> bool:
        return self._active_principal() is not None

    def has_permission(self, permission_code: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        return permission_code in principal.permissions

    def has_any_project_access(self, permission_code: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return permission_code in principal.permissions
        if permission_code not in principal.permissions:
            return False
        return any(permission_code in perms for perms in principal.project_access.values())

    def has_project_permission(self, project_id: str, permission_code: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return permission_code in principal.permissions
        if permission_code not in principal.permissions:
            return False
        access_map = principal.project_access or {}
        if not access_map:
            return True
        return permission_code in access_map.get(project_id, frozenset())

    def project_ids_for(self, permission_code: str) -> set[str]:
        principal = self._active_principal()
        if principal is None:
            return set()
        return {
            project_id
            for project_id, permissions in (principal.project_access or {}).items()
            if permission_code in permissions
        }

    def is_project_restricted(self) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return False
        return bool(principal.project_access)

    def _active_principal(self) -> UserSessionPrincipal | None:
        principal = self._principal
        if principal is None:
            return None
        expires_at = ensure_utc_datetime(principal.session_expires_at)
        if expires_at != principal.session_expires_at:
            principal = replace(principal, session_expires_at=expires_at)
            self._principal = principal
        if expires_at is not None and datetime.now(timezone.utc) >= expires_at:
            self.clear()
            return None
        return principal


__all__ = ["UserSessionPrincipal", "UserSessionContext"]
