from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from .auth_service import AuthService


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
        raise BusinessRuleError(
            f"{operation_label.capitalize()} is restricted to the authenticated user.",
            code="AUTH_SELF_SERVICE_REQUIRED",
        )


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
        raise BusinessRuleError(
            "Tenant membership authorization is not configured.",
            code="AUTHORIZATION_CONTEXT_REQUIRED",
        )
    active_tenant_id = (
        str(service._user_session.active_tenant_id() or "").strip() or None
    )
    if active_tenant_id is None:
        raise BusinessRuleError(
            f"Active tenant context is required to {operation_label}.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    if not service._user_tenant_repo.is_active_member(
        principal.user_id,
        active_tenant_id,
    ):
        raise BusinessRuleError(
            "The authenticated user is not an active member of the selected tenant.",
            code="TENANT_ACCESS_DENIED",
        )
    if not service._user_tenant_repo.is_active_member(
        str(target_user_id or "").strip(),
        active_tenant_id,
    ):
        raise BusinessRuleError(
            f"Cannot {operation_label} for a user outside the active tenant.",
            code=denial_code,
        )
    return active_tenant_id


__all__ = [
    "is_platform_operator",
    "require_self_target",
    "require_target_user_in_active_tenant",
]
