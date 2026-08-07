from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import authorization_denied
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.platform.application.security.auth.auth_service import AuthService


def _current_principal(service: AuthService):
    if service._user_session is None or service._user_session.principal is None:
        raise BusinessRuleError(
            "Authentication is required for this account operation.",
            code="AUTHENTICATION_REQUIRED",
        )
    return service._user_session.principal


def is_platform_operator(service: AuthService) -> bool:
    principal = _current_principal(service)
    return (
        "admin" in principal.role_names
        and "platform.admin" in principal.permissions
    )


def require_self_target(
    service: AuthService,
    target_user_id: str,
    *,
    operation_label: str,
) -> None:
    principal = _current_principal(service)
    if principal.user_id != str(target_user_id or "").strip():
        authorization_denied(
            service._user_session,
            message=f"{operation_label.capitalize()} is restricted to the authenticated user.",
            code="AUTH_SELF_SERVICE_REQUIRED",
            operation_label=operation_label,
            target_scope_type="user",
            target_scope_id=target_user_id,
            operation="authorization.target.denied",
        )


def require_actor_active_tenant(
    service: AuthService,
    *,
    operation_label: str,
) -> str:
    principal = _current_principal(service)
    if service._user_session is None:
        authorization_denied(
            service._user_session,
            message="Authentication context is not configured.",
            code="AUTHORIZATION_CONTEXT_REQUIRED",
            operation_label=operation_label,
            operation="authorization.infrastructure.denied",
        )
    active_tenant_id = str(
        service._user_session.active_tenant_id() or ""
    ).strip()
    if not active_tenant_id:
        authorization_denied(
            service._user_session,
            message=f"Active tenant context is required to {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
            operation_label=operation_label,
            target_scope_type="tenant",
            operation="authorization.context.denied",
        )
    if service._tenant_context_service is None:
        authorization_denied(
            service._user_session,
            message="Tenant context authorization is not configured.",
            code="AUTHORIZATION_CONTEXT_REQUIRED",
            operation_label=operation_label,
            target_scope_type="tenant",
            target_scope_id=active_tenant_id,
            operation="authorization.infrastructure.denied",
        )
    validated_tenant_id = service._tenant_context_service.require_active_tenant_id(
        operation_label=operation_label,
    )
    if validated_tenant_id != active_tenant_id:
        authorization_denied(
            service._user_session,
            message="The selected tenant context is inconsistent.",
            code="TENANT_CONTEXT_MISMATCH",
            operation_label=operation_label,
            target_scope_type="tenant",
            target_scope_id=active_tenant_id,
            operation="authorization.context.denied",
        )
    if service._user_tenant_repo is None:
        authorization_denied(
            service._user_session,
            message="Tenant membership authorization is not configured.",
            code="AUTHORIZATION_CONTEXT_REQUIRED",
            operation_label=operation_label,
            target_scope_type="tenant",
            target_scope_id=active_tenant_id,
            operation="authorization.infrastructure.denied",
        )
    if (
        not is_platform_operator(service)
        and not service._user_tenant_repo.is_active_member(
            principal.user_id,
            active_tenant_id,
        )
    ):
        authorization_denied(
            service._user_session,
            message="The authenticated user is not an active member of the selected tenant.",
            code="TENANT_ACCESS_DENIED",
            operation_label=operation_label,
            target_scope_type="tenant",
            target_scope_id=active_tenant_id,
            operation="authorization.membership.denied",
        )
    return active_tenant_id


def require_target_user_in_customer_tenant(
    service: AuthService,
    target_user_id: str,
    *,
    operation_label: str,
    denial_code: str = "USER_CROSS_TENANT_DENIED",
) -> str:
    active_tenant_id = require_actor_active_tenant(
        service,
        operation_label=operation_label,
    )
    if not service._user_tenant_repo.is_active_member(
        str(target_user_id or "").strip(),
        active_tenant_id,
    ):
        authorization_denied(
            service._user_session,
            message=f"Cannot {operation_label} for a user outside the active tenant.",
            code=denial_code,
            operation_label=operation_label,
            target_scope_type="user",
            target_scope_id=target_user_id,
            operation="authorization.membership.denied",
        )
    return active_tenant_id


def require_target_user_in_active_tenant(
    service: AuthService,
    target_user_id: str,
    *,
    operation_label: str,
    denial_code: str = "USER_CROSS_TENANT_DENIED",
) -> str:
    principal = _current_principal(service)
    if is_platform_operator(service):
        return ""
    if service._user_tenant_repo is None:
        authorization_denied(
            service._user_session,
            message="Tenant membership authorization is not configured.",
            code="AUTHORIZATION_CONTEXT_REQUIRED",
            operation_label=operation_label,
            operation="authorization.infrastructure.denied",
        )
    active_tenant_id = (
        str(service._user_session.active_tenant_id() or "").strip() or None
    )
    if active_tenant_id is None:
        authorization_denied(
            service._user_session,
            message=f"Active tenant context is required to {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
            operation_label=operation_label,
            target_scope_type="tenant",
            operation="authorization.context.denied",
        )
    if not service._user_tenant_repo.is_active_member(
        principal.user_id,
        active_tenant_id,
    ):
        authorization_denied(
            service._user_session,
            message="The authenticated user is not an active member of the selected tenant.",
            code="TENANT_ACCESS_DENIED",
            operation_label=operation_label,
            target_scope_type="tenant",
            target_scope_id=active_tenant_id,
            operation="authorization.membership.denied",
        )
    if not service._user_tenant_repo.is_active_member(
        str(target_user_id or "").strip(),
        active_tenant_id,
    ):
        authorization_denied(
            service._user_session,
            message=f"Cannot {operation_label} for a user outside the active tenant.",
            code=denial_code,
            operation_label=operation_label,
            target_scope_type="user",
            target_scope_id=target_user_id,
            operation="authorization.membership.denied",
        )
    return active_tenant_id


__all__ = [
    "is_platform_operator",
    "require_actor_active_tenant",
    "require_self_target",
    "require_target_user_in_customer_tenant",
    "require_target_user_in_active_tenant",
]
