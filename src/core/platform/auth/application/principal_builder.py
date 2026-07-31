from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.auth.domain.session import UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.platform.auth.domain import UserAccount

    from .auth_service import AuthService


_CONTEXT_UNSET = object()


# RBAC-TRANSITION-ONLY: Remove this legacy scoped-grant/project-membership
# projection after each resource policy writes canonical role bindings.
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


def _merge_scoped_access(
    *sources: dict[str, dict[str, frozenset[str]]],
) -> dict[str, dict[str, frozenset[str]]]:
    merged: dict[str, dict[str, frozenset[str]]] = {}
    for source in sources:
        for scope_type, scope_rows in source.items():
            target_rows = merged.setdefault(scope_type, {})
            for scope_id, permissions in scope_rows.items():
                target_rows[scope_id] = frozenset(
                    set(target_rows.get(scope_id, frozenset())).union(
                        permissions
                    )
                )
    return merged


def build_principal(
    service: AuthService,
    user: UserAccount,
    *,
    session_id: str | None = None,
    active_tenant_id: str | None | object = _CONTEXT_UNSET,
    active_organization_id: str | None | object = _CONTEXT_UNSET,
) -> UserSessionPrincipal:
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
    canonical_authority = (
        service._require_canonical_role_resolver().resolve_organization_authority(
            user.id,
            tenant_id=resolved_tenant_id,
            organization_id=resolved_organization_id,
        )
    )
    transitional_scoped_access = _load_scoped_access(
        service,
        user.id,
        tenant_id=resolved_tenant_id,
        organization_id=resolved_organization_id,
    )
    scoped_access = _merge_scoped_access(
        canonical_authority.scoped_access,
        transitional_scoped_access,
    )
    project_access = dict(scoped_access.get("project", {}))
    return UserSessionPrincipal(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_names=canonical_authority.role_names,
        permissions=canonical_authority.permissions,
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
