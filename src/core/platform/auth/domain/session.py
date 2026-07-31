from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from pydantic import field_validator

from src.core.platform.common.ids import generate_id
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain.user import (
    normalize_auth_device_label,
    normalize_auth_session_revision,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)

if TYPE_CHECKING:
    from src.core.platform.authorization import SecurityDenialEvent


def normalize_auth_session_user_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="User id is required.",
        code="USER_ID_REQUIRED",
    )


def normalize_auth_session_auth_method(value: object) -> str:
    return normalize_required_text(
        value,
        message="Authentication method is required.",
        code="AUTH_SESSION_AUTH_METHOD_REQUIRED",
    ).lower()


def normalize_auth_session_context_id(value: object) -> str | None:
    return normalize_optional_identifier(value)


def normalize_auth_session_datetime(
    value: object,
    *,
    code: str,
    required: bool = False,
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValidationError(
                "Auth session expiry is required.",
                code=code,
            )
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Auth session timestamps must be valid datetimes.",
            code=code,
        )
    return ensure_utc_datetime(value)


@validated_dataclass
class AuthSession:
    id: str
    user_id: str
    session_revision: int
    auth_method: str
    device_label: str | None = None
    last_active_tenant_id: str | None = None
    last_active_organization_id: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    last_validated_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, value: object) -> str:
        return normalize_auth_session_user_id(value)

    @field_validator("session_revision", mode="before")
    @classmethod
    def _validate_session_revision(cls, value: object) -> int:
        return normalize_auth_session_revision(value)

    @field_validator("auth_method", mode="before")
    @classmethod
    def _validate_auth_method(cls, value: object) -> str:
        return normalize_auth_session_auth_method(value)

    @field_validator("device_label", mode="before")
    @classmethod
    def _normalize_device_label(cls, value: object) -> str | None:
        return normalize_auth_device_label(value)

    @field_validator("last_active_tenant_id", "last_active_organization_id", mode="before")
    @classmethod
    def _normalize_context_ids(cls, value: object) -> str | None:
        return normalize_auth_session_context_id(value)

    @field_validator("issued_at", "last_validated_at", "revoked_at", "created_at", "updated_at", mode="before")
    @classmethod
    def _validate_optional_datetimes(cls, value: object) -> datetime | None:
        return normalize_auth_session_datetime(
            value,
            code="AUTH_SESSION_TIMESTAMP_INVALID",
        )

    @field_validator("expires_at", mode="before")
    @classmethod
    def _validate_expires_at(cls, value: object) -> datetime | None:
        return normalize_auth_session_datetime(
            value,
            code="AUTH_SESSION_EXPIRES_AT_INVALID",
            required=True,
        )

    @staticmethod
    def create(
        *,
        user_id: str,
        session_revision: int,
        auth_method: str,
        expires_at: datetime,
        device_label: str | None = None,
        last_active_tenant_id: str | None = None,
        last_active_organization_id: str | None = None,
    ) -> "AuthSession":
        now = datetime.now(timezone.utc)
        return AuthSession(
            id=generate_id(),
            user_id=user_id,
            session_revision=session_revision,
            auth_method=auth_method,
            device_label=device_label,
            last_active_tenant_id=last_active_tenant_id,
            last_active_organization_id=last_active_organization_id,
            issued_at=now,
            expires_at=expires_at,
            last_validated_at=now,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )


def _normalize_permission_set(values: Iterable[str] | None) -> frozenset[str]:
    return frozenset(
        str(value).strip()
        for value in (values or ())
        if str(value).strip()
    )


def _normalize_scoped_access(
    scoped_access: Mapping[str, Mapping[str, Iterable[str] | frozenset[str]]] | None,
    project_access: Mapping[str, Iterable[str] | frozenset[str]] | None = None,
) -> dict[str, dict[str, frozenset[str]]]:
    normalized: dict[str, dict[str, frozenset[str]]] = {}

    def _merge(scope_type: str, scope_id: str, permissions: Iterable[str] | frozenset[str]) -> None:
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
    role_names: frozenset[str]
    permissions: frozenset[str]
    scoped_access: dict[str, dict[str, frozenset[str]]] = field(default_factory=dict)
    project_access: dict[str, frozenset[str]] = field(default_factory=dict)
    session_expires_at: datetime | None = None
    must_change_password: bool = False
    session_revision: int = 1
    identity_provider: str | None = None
    last_login_auth_method: str | None = None
    session_id: str | None = None
    active_tenant_id: str | None = None
    active_organization_id: str | None = None


class UserSessionContext:
    def __init__(
        self,
        *,
        principal_validator: (
            Callable[[UserSessionPrincipal], UserSessionPrincipal | None] | None
        ) = None,
        context_listener: Callable[["UserSessionContext"], None] | None = None,
        security_denial_listener: (
            Callable[["SecurityDenialEvent"], None] | None
        ) = None,
    ):
        self._principal: UserSessionPrincipal | None = None
        self._principal_validator = principal_validator
        self._context_listener = context_listener
        self._security_denial_listener = security_denial_listener
        self._active_tenant_id: str | None = None
        self._active_organization_id: str | None = None

    @property
    def principal(self) -> UserSessionPrincipal | None:
        return self._principal

    def set_principal(self, principal: UserSessionPrincipal) -> None:
        normalized = self._normalize_principal(principal)
        self._principal = normalized
        self._restore_active_context_from_principal(normalized)
        self._notify_context_changed()

    def set_validator(
        self,
        validator: Callable[[UserSessionPrincipal], UserSessionPrincipal | None] | None,
    ) -> None:
        self._principal_validator = validator

    def set_context_listener(
        self,
        listener: Callable[["UserSessionContext"], None] | None,
    ) -> None:
        self._context_listener = listener

    def set_security_denial_listener(
        self,
        listener: Callable[["SecurityDenialEvent"], None] | None,
    ) -> None:
        self._security_denial_listener = listener

    def record_security_denial(self, event: "SecurityDenialEvent") -> bool:
        listener = self._security_denial_listener
        if listener is None:
            return False
        listener(event)
        return True

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
            active_tenant_id=(
                str(getattr(principal, "active_tenant_id", "") or "").strip() or None
            ),
            active_organization_id=(
                str(getattr(principal, "active_organization_id", "") or "").strip() or None
            ),
        )

    def clear(self) -> None:
        self._principal = None
        self._active_tenant_id = None
        self._active_organization_id = None
        self._notify_context_changed()

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

    def organization_ids(self) -> set[str]:
        principal = self._active_principal()
        if principal is None:
            return set()
        return set(self._scope_rows(principal, "organization").keys())

    def has_organization_access(self, organization_id: str) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        if "admin" in principal.role_names:
            return True
        normalized_organization_id = str(organization_id or "").strip()
        if not normalized_organization_id:
            return False
        organization_ids = self.organization_ids()
        return normalized_organization_id in organization_ids

    def is_platform_admin(self) -> bool:
        principal = self._active_principal()
        if principal is None:
            return False
        return "platform.admin" in principal.permissions

    def set_active_tenant_id(self, tenant_id: str | None) -> None:
        normalized = str(tenant_id or "").strip() or None
        if normalized == self._active_tenant_id:
            return
        self._active_tenant_id = normalized
        if self._principal is not None:
            self._principal = replace(self._principal, active_tenant_id=normalized)
        self._notify_context_changed()

    def active_tenant_id(self) -> str | None:
        session_tenant_id = str(self._active_tenant_id or "").strip() or None
        if session_tenant_id:
            return session_tenant_id
        principal = self._active_principal()
        if principal is None:
            return None
        return str(getattr(principal, "active_tenant_id", "") or "").strip() or None

    def stored_active_tenant_id(self) -> str | None:
        return str(self._active_tenant_id or "").strip() or None

    def set_active_organization_id(self, organization_id: str | None) -> None:
        normalized = str(organization_id or "").strip() or None
        if normalized == self._active_organization_id:
            return
        self._active_organization_id = normalized
        if self._principal is not None:
            self._principal = replace(self._principal, active_organization_id=normalized)
        self._notify_context_changed()

    def active_organization_id(self) -> str | None:
        session_organization_id = str(self._active_organization_id or "").strip() or None
        if session_organization_id:
            return session_organization_id
        principal = self._active_principal()
        if principal is None:
            return None
        principal_organization_id = (
            str(getattr(principal, "active_organization_id", "") or "").strip()
            or None
        )
        if principal_organization_id:
            # H-2: only return org from principal when tenant context is consistent.
            # Prevents a stale org_id (from a previous tenant) leaking through this fallback.
            principal_tenant_id = str(getattr(principal, "active_tenant_id", "") or "").strip() or None
            current_tenant_id = str(self._active_tenant_id or "").strip() or None
            if current_tenant_id is None or current_tenant_id == principal_tenant_id:
                return principal_organization_id
        return None

    def stored_active_organization_id(self) -> str | None:
        return str(self._active_organization_id or "").strip() or None

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
        if validator is not None and principal.session_id:
            validated = validator(principal)
            if validated is None:
                self.clear()
                return None
            normalized = self._normalize_principal(validated)
            if normalized != principal:
                principal = normalized
                self._principal = principal
                self._restore_active_context_from_principal(principal)
                self._notify_context_changed()
        return principal

    def _restore_active_context_from_principal(
        self,
        principal: UserSessionPrincipal | None,
    ) -> None:
        if principal is None:
            return
        tenant_id = str(
            getattr(principal, "active_tenant_id", "") or ""
        ).strip() or None
        organization_id = str(
            getattr(principal, "active_organization_id", "") or ""
        ).strip() or None
        self._active_tenant_id = tenant_id
        self._active_organization_id = organization_id if tenant_id else None

    def _notify_context_changed(self) -> None:
        listener = self._context_listener
        if listener is not None:
            listener(self)

    @staticmethod
    def _scope_rows(
        principal: UserSessionPrincipal,
        scope_type: str,
    ) -> dict[str, frozenset[str]]:
        normalized_scope_type = str(scope_type or "").strip().lower()
        if not normalized_scope_type:
            return {}
        return dict((principal.scoped_access or {}).get(normalized_scope_type, {}))


__all__ = [
    "AuthSession",
    "UserSessionContext",
    "UserSessionPrincipal",
    "normalize_auth_session_auth_method",
    "normalize_auth_session_context_id",
    "normalize_auth_session_datetime",
    "normalize_auth_session_user_id",
]
