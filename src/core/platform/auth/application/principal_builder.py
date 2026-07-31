from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain.session import UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


_CONTEXT_UNSET = object()


def _permissions_for_role_ids(
    service: AuthService,
    role_ids: set[str],
) -> set[str]:
    permission_ids: set[str] = set()
    for role_id in role_ids:
        permission_ids.update(
            service._role_permission_repo.list_permission_ids(role_id)
        )
    permission_codes = {
        permission.id: permission.code
        for permission in service._permission_repo.list_all()
    }
    return {
        permission_codes[permission_id]
        for permission_id in permission_ids
        if permission_id in permission_codes
    }


def _role_names_by_id(
    service: AuthService,
    role_ids: set[str],
) -> dict[str, str]:
    names: dict[str, str] = {}
    for role_id in role_ids:
        role = service._role_repo.get(role_id)
        if role is not None:
            names[role_id] = role.name
    return names


def _load_scoped_access(
    service: AuthService,
    user_id: str,
    *,
    tenant_id: str | None,
    organization_id: str | None,
) -> dict[str, dict[str, frozenset[str]]]:
    scoped_access: dict[str, dict[str, frozenset[str]]] = {}
    if tenant_id is None:
        return scoped_access
    if service._scoped_access_repo is not None:
        try:
            grants = service._scoped_access_repo.list_by_user_for_context(
                user_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
        except NotImplementedError as exc:
            raise BusinessRuleError(
                "Explicit-context scoped access reads are not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
            ) from exc
        for grant in grants:
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
        try:
            memberships = (
                service._project_membership_repo.list_by_user_for_context(
                    user_id,
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                )
            )
        except NotImplementedError as exc:
            raise BusinessRuleError(
                "Explicit-context project access reads are not configured.",
                code="AUTHORIZATION_CONTEXT_REQUIRED",
            ) from exc
        for membership in memberships:
            permissions = frozenset(
                str(code).strip()
                for code in membership.permission_codes
                if str(code).strip()
            )
            if permissions:
                scoped_access["project"][membership.project_id] = permissions
        if not scoped_access["project"]:
            scoped_access.pop("project", None)
    return scoped_access


def build_principal(
    service: AuthService,
    user: UserAccount,
    *,
    session_id: str | None = None,
    active_tenant_id: str | None | object = _CONTEXT_UNSET,
    active_organization_id: str | None | object = _CONTEXT_UNSET,
) -> UserSessionPrincipal:
    # RBAC-TRANSITION-ONLY: Legacy-authoritative principal construction.
    # Remove after canonical building owns login, restore, and context switching.
    context_is_explicit = (
        active_tenant_id is not _CONTEXT_UNSET
        or active_organization_id is not _CONTEXT_UNSET
    )
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

    platform_authority = service._canonical_platform_authority(user.id)
    global_role_ids = service._legacy_customer_role_ids(user.id)
    global_role_names = _role_names_by_id(service, global_role_ids)
    global_permissions = _permissions_for_role_ids(
        service,
        global_role_ids,
    ).union(platform_authority.permissions)
    is_platform_operator = (
        "platform.admin" in platform_authority.permissions
    )

    if active_tenant_id is _CONTEXT_UNSET:
        resolved_tenant_id = (
            str(getattr(resolved_session, "last_active_tenant_id", "") or "").strip()
            or None
        )
        if (
            resolved_tenant_id is None
            and service._tenant_context_service is not None
        ):
            resolved_tenant_id = (
                service._tenant_context_service.initial_tenant_id_for_user(user.id)
            )
    else:
        resolved_tenant_id = str(active_tenant_id or "").strip() or None

    if active_organization_id is _CONTEXT_UNSET:
        session_tenant_id = (
            str(getattr(resolved_session, "last_active_tenant_id", "") or "").strip()
            or None
        )
        resolved_organization_id = (
            str(
                getattr(
                    resolved_session,
                    "last_active_organization_id",
                    "",
                )
                or ""
            ).strip()
            or None
            if session_tenant_id == resolved_tenant_id
            else None
        )
        if (
            resolved_tenant_id is not None
            and resolved_organization_id is None
            and (resolved_session is None or session_tenant_id is None)
            and service._tenant_context_service is not None
        ):
            resolved_organization_id = (
                service._tenant_context_service.initial_organization_id_for_tenant(
                    resolved_tenant_id
                )
            )
            resolved_tenant_id, resolved_organization_id = (
                service._tenant_context_service.validate_principal_context(
                    user_id=user.id,
                    is_platform_operator=is_platform_operator,
                    tenant_id=resolved_tenant_id,
                    organization_id=resolved_organization_id,
                )
            )
    else:
        resolved_organization_id = (
            str(active_organization_id or "").strip() or None
        )

    if service._tenant_context_service is not None:
        try:
            resolved_tenant_id, resolved_organization_id = (
                service._tenant_context_service.validate_principal_context(
                    user_id=user.id,
                    is_platform_operator=is_platform_operator,
                    tenant_id=resolved_tenant_id,
                    organization_id=resolved_organization_id,
                )
            )

        except BusinessRuleError:
            if context_is_explicit or resolved_tenant_id is None:
                raise
            resolved_organization_id = (
                service._tenant_context_service.initial_organization_id_for_tenant(
                    resolved_tenant_id
                )
            )

    if (
        is_platform_operator
        and resolved_tenant_id is not None
        and not service._allow_platform_customer_context
    ):
        raise BusinessRuleError(
            "Platform authority cannot enter ordinary customer context.",
            code="PLATFORM_CUSTOMER_CONTEXT_DENIED",
        )
    scoped_access = _load_scoped_access(
        service,
        user.id,
        tenant_id=resolved_tenant_id,
        organization_id=resolved_organization_id,
    )

    membership_ids = (
        service._user_tenant_repo.list_tenant_ids_for_user(user.id)
        if service._user_tenant_repo is not None
        else []
    )
    effective_role_ids = set(global_role_ids)
    tenant_admin_ids = {
        role_id
        for role_id, role_name in global_role_names.items()
        if role_name == "tenant_admin"
    }
    if tenant_admin_ids and not is_platform_operator:
        is_unambiguous_tenant_admin = (
            len(membership_ids) == 1
            and resolved_tenant_id == membership_ids[0]
        )
        if resolved_tenant_id is not None and len(membership_ids) > 1:
            raise BusinessRuleError(
                "Legacy tenant administrator scope is ambiguous and requires migration.",
                code="LEGACY_TENANT_ADMIN_AMBIGUOUS",
            )
        if not is_unambiguous_tenant_admin:
            effective_role_ids.difference_update(tenant_admin_ids)

    organization_role_ids: set[str] = set()
    if resolved_organization_id is not None:
        organization_role_ids.update(
            service._user_role_repo.list_role_ids_for_organization(
                user.id,
                resolved_organization_id,
            )
        )
        effective_role_ids.update(organization_role_ids)

    effective_role_names = _role_names_by_id(service, effective_role_ids)
    global_org_admin_ids = {
        role_id
        for role_id, role_name in global_role_names.items()
        if role_name == "org_admin"
    }
    organization_scope_ids = set(
        scoped_access.get("organization", {}).keys()
    )
    has_explicit_org_admin_scope = (
        resolved_organization_id is not None
        and (
            resolved_organization_id in organization_scope_ids
            or any(
                effective_role_names.get(role_id) == "org_admin"
                for role_id in organization_role_ids
            )
        )
    )
    if (
        global_org_admin_ids
        and not is_platform_operator
        and not has_explicit_org_admin_scope
    ):
        effective_role_ids.difference_update(global_org_admin_ids)
        effective_role_names = _role_names_by_id(service, effective_role_ids)

    project_access = dict(scoped_access.get("project", {}))
    return UserSessionPrincipal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_names=frozenset(
            set(effective_role_names.values()).union(
                platform_authority.role_names
            )
        ),
        permissions=frozenset(
            _permissions_for_role_ids(service, effective_role_ids).union(
                platform_authority.permissions
            )
        ),
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
        active_tenant_id=resolved_tenant_id,
        active_organization_id=resolved_organization_id,
    )


__all__ = ["build_principal"]
