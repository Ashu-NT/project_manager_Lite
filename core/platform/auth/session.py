from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Callable, FrozenSet

from core.platform.auth.datetime_utils import ensure_utc_datetime


def _normalize_permission_set(values: Iterable[str] | None) -> FrozenSet[str]:
    return frozenset(
        str(value).strip()
        for value in (values or ())
        if str(value).strip()
    )


def _normalize_scoped_access(
    scoped_access: Mapping[str, Mapping[str, Iterable[str] | FrozenSet[str]]] | None,
    project_access: Mapping[str, Iterable[str] | FrozenSet[str]] | None = None,
) -> dict[str, dict[str, FrozenSet[str]]]:
    normalized: dict[str, dict[str, FrozenSet[str]]] = {}

    def _merge(scope_type: str, scope_id: str, permissions: Iterable[str] | FrozenSet[str]) -> None:
        normalized_scope_type = str(scope_type or "").strip().lower()
        normalized_scope_id = str(scope_id or "").strip()
        if not normalized_scope_type or not normalized_scope_id:
            return
        normalized_permissions = _normalize_permission_set(permissions)
        if not normalized_permissions:
            return
        scope_rows = normalized.setdefault(normalized_scope_type, {})
        existing = scope_rows.get(normalized_scope_id, frozenset())
        scope_rows[normalized_scope_id] = frozenset(set(existing).union(normalized_permissions))

    for raw_scope_type, raw_scope_rows in (scoped_access or {}).items():
        if not isinstance(raw_scope_rows, Mapping):
            continue
        for raw_scope_id, raw_permissions in raw_scope_rows.items():
            _merge(str(raw_scope_type), str(raw_scope_id), raw_permissions)

    for raw_project_id, raw_permissions in (project_access or {}).items():
        _merge("project", str(raw_project_id), raw_permissions)

    return {
        scope_type: dict(scope_rows)
        for scope_type, scope_rows in normalized.items()
    }


@dataclass(frozen=True)
class UserSessionPrincipal:
    user_id: str
    username: str
    display_name: str | None
    role_names: FrozenSet[str]
    permissions: FrozenSet[str]
    scoped_access: dict[str, dict[str, FrozenSet[str]]] = field(default_factory=dict)
    project_access: dict[str, FrozenSet[str]] = field(default_factory=dict)
    session_expires_at: datetime | None = None
    must_change_password: bool = False
    session_revision: int = 1
    identity_provider: str | None = None
    last_login_auth_method: str | None = None
    session_id: str | None = None


class UserSessionContext:
    def __init__(
        self,
        *,
        principal_validator: Callable[[UserSessionPrincipal], UserSessionPrincipal | None] | None = None,
    ):
        self._principal: UserSessionPrincipal | None = None
        self._principal_validator = principal_validator

    @property
    def principal(self) -> UserSessionPrincipal | None:
        return self._principal

    def set_principal(self, principal: UserSessionPrincipal) -> None:
        self._principal = self._normalize_principal(principal)

    def set_validator(
        self,
        validator: Callable[[UserSessionPrincipal], UserSessionPrincipal | None] | None,
    ) -> None:
        self._principal_validator = validator

    def _normalize_principal(self, principal: UserSessionPrincipal) -> UserSessionPrincipal:
        normalized_scoped_access = _normalize_scoped_access(
            principal.scoped_access,
            principal.project_access,
        )
        return replace(
            principal,
            permissions=_normalize_permission_set(principal.permissions),
            scoped_access=normalized_scoped_access,
            project_access=dict(normalized_scoped_access.get("project", {})),
            session_expires_at=ensure_utc_datetime(principal.session_expires_at),
            must_change_password=bool(getattr(principal, "must_change_password", False)),
            session_revision=max(1, int(getattr(principal, "session_revision", 1) or 1)),
            identity_provider=(str(getattr(principal, "identity_provider", "") or "").strip() or None),
            last_login_auth_method=(str(getattr(principal, "last_login_auth_method", "") or "").strip() or None),
            session_id=(str(getattr(principal, "session_id", "") or "").strip() or None),
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

    def has_any_scope_access(self, scope_type: str, permission_code: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return permission_code in principal.permissions
        if permission_code not in principal.permissions:
            return False
        scope_rows = self._scope_rows(principal, scope_type)
        if not scope_rows:
            return True
        return any(permission_code in permissions for permissions in scope_rows.values())

    def has_scope_permission(self, scope_type: str, scope_id: str, permission_code: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return permission_code in principal.permissions
        if permission_code not in principal.permissions:
            return False
        scope_rows = self._scope_rows(principal, scope_type)
        if not scope_rows:
            return True
        return permission_code in scope_rows.get(str(scope_id or "").strip(), frozenset())

    def has_any_project_access(self, permission_code: str) -> bool:
        return self.has_any_scope_access("project", permission_code)

    def has_project_permission(self, project_id: str, permission_code: str) -> bool:
        return self.has_scope_permission("project", project_id, permission_code)

    def scope_ids_for(self, scope_type: str, permission_code: str) -> set[str]:
        principal = self._active_principal()
        if principal is None:
            return set()
        return {
            scope_id
            for scope_id, permissions in self._scope_rows(principal, scope_type).items()
            if permission_code in permissions
        }

    def project_ids_for(self, permission_code: str) -> set[str]:
        return self.scope_ids_for("project", permission_code)

    def is_scope_restricted(self, scope_type: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return False
        return bool(self._scope_rows(principal, scope_type))

    def is_project_restricted(self) -> bool:
        return self.is_scope_restricted("project")

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
        validator = self._principal_validator
        if validator is not None:
            validated = validator(principal)
            if validated is None:
                self.clear()
                return None
            normalized = self._normalize_principal(validated)
            if normalized != principal:
                principal = normalized
                self._principal = principal
        return principal

    @staticmethod
    def _scope_rows(
        principal: UserSessionPrincipal,
        scope_type: str,
    ) -> dict[str, FrozenSet[str]]:
        normalized_scope_type = str(scope_type or "").strip().lower()
        if not normalized_scope_type:
            return {}
        return dict((principal.scoped_access or {}).get(normalized_scope_type, {}))


__all__ = ["UserSessionPrincipal", "UserSessionContext"]
