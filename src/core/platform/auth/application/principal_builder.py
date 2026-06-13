from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain.session import UserSessionPrincipal

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


def build_principal(service: AuthService, user: UserAccount, *, session_id: str | None = None) -> UserSessionPrincipal:
    scoped_access: dict[str, dict[str, frozenset[str]]] = {}
    if service._scoped_access_repo is not None:
        for grant in service._scoped_access_repo.list_by_user(user.id):
            scope_type = str(grant.scope_type or "").strip().lower()
            scope_id = str(grant.scope_id or "").strip()
            if not scope_type or not scope_id:
                continue
            permissions = frozenset(
                str(code).strip()
                for code in grant.permission_codes
                if str(code).strip()
            )
            if not permissions:
                continue
            scope_rows = scoped_access.setdefault(scope_type, {})
            existing = scope_rows.get(scope_id, frozenset())
            scope_rows[scope_id] = frozenset(set(existing).union(permissions))
    elif service._project_membership_repo is not None:
        scoped_access["project"] = {}
        for membership in service._project_membership_repo.list_by_user(user.id):
            permissions = frozenset(
                str(code).strip()
                for code in membership.permission_codes
                if str(code).strip()
            )
            if permissions:
                scoped_access["project"][membership.project_id] = permissions
        if not scoped_access["project"]:
            scoped_access.pop("project", None)
    project_access = dict(scoped_access.get("project", {}))
    resolved_session_id = (
        str(session_id or "").strip()
        or str(getattr(user, "active_session_id", "") or "").strip()
        or None
    )
    resolved_session = (
        service._auth_session_repo.get(resolved_session_id)
        if service._auth_session_repo is not None and resolved_session_id is not None
        else None
    )
    if resolved_session is not None and resolved_session.revoked_at is not None:
        resolved_session = None
        resolved_session_id = None
    return UserSessionPrincipal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_names=frozenset(service.get_user_role_names(user.id)),
        permissions=frozenset(service.get_user_permissions(user.id)),
        scoped_access=scoped_access,
        project_access=project_access,
        session_expires_at=ensure_utc_datetime(
            resolved_session.expires_at if resolved_session is not None else user.session_expires_at
        ),
        must_change_password=bool(user.must_change_password),
        session_revision=int(getattr(user, "session_revision", 1) or 1),
        identity_provider=getattr(user, "identity_provider", None),
        last_login_auth_method=(
            resolved_session.auth_method
            if resolved_session is not None
            else getattr(user, "last_login_auth_method", None)
        ),
        session_id=resolved_session_id,
        active_tenant_id=(
            getattr(resolved_session, "last_active_tenant_id", None)
            if resolved_session is not None
            else None
        ),
        active_organization_id=(
            getattr(resolved_session, "last_active_organization_id", None)
            if resolved_session is not None
            else None
        ),
    )


__all__ = ["build_principal"]
