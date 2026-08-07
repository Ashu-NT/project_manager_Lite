from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    authorization_denied,
    require_permission,
)
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_TENANT,
)

from src.core.platform.application.security.auth.session.session_service import refresh_current_session_if_user
from src.core.platform.application.security.authorization.roles.role_scope_policy import (
    EXPLICIT_SCOPE_ROLE_NAMES,
    PLATFORM_ROLE_NAMES,
    normalize_role_name,
)
from src.core.platform.application.security.authorization.enforcement.target_user_authorization import (
    require_target_user_in_customer_tenant,
)

if TYPE_CHECKING:
    from src.core.platform.application.security.auth.auth_service import AuthService

def _require_canonical_target_membership(
    service: AuthService,
    target_user_id: str,
    *,
    tenant_id: str,
    operation: str,
) -> None:
    if (
        service._user_tenant_repo is not None
        and service._user_tenant_repo.is_active_member(
            target_user_id,
            tenant_id,
        )
    ):
        return
    authorization_denied(
        service._user_session,
        message="The user is not an active member of the selected tenant.",
        code="ROLE_TARGET_TENANT_DENIED",
        operation_label=f"{operation} a canonical tenant role",
        target_scope_type="user",
        target_scope_id=target_user_id,
        operation="authorization.membership.denied",
    )


def assign_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="assign role")
    tenant_id = service._tenant_context_service.require_active_tenant_id(
        operation_label="assign role"
    )
    role = service._require_tenant_role_by_name(tenant_id, role_name)
    if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
        authorization_denied(
            service._user_session,
            message="Platform roles require the dedicated provisioning workflow.",
            code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
            operation_label="assign a platform role",
            target_scope_type="role",
            target_scope_id=role.id,
            operation="authorization.platform_role.denied",
        )
    if role.allowed_scope_type != ROLE_SCOPE_TENANT:
        authorization_denied(
            service._user_session,
            message=(
                f"Role '{role.name}' requires an explicit "
                f"{role.allowed_scope_type} scope."
            ),
            code="ROLE_SCOPE_REQUIRED",
            operation_label="assign a scoped role",
            target_scope_type="role",
            target_scope_id=role.id,
            operation="authorization.resource_scope.denied",
        )
    user = service._require_user(user_id)
    _require_canonical_target_membership(
        service,
        user.id,
        tenant_id=tenant_id,
        operation="assign",
    )
    service._require_role_governance_service().assign_role(
        target_user_id=user.id,
        role_id=role.id,
    )
    refresh_current_session_if_user(service, user.id)


def revoke_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="revoke role")
    tenant_id = service._tenant_context_service.require_active_tenant_id(
        operation_label="revoke role"
    )
    role = service._require_tenant_role_by_name(tenant_id, role_name)
    if role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
        authorization_denied(
            service._user_session,
            message="Platform roles require the dedicated provisioning workflow.",
            code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
            operation_label="revoke a platform role",
            target_scope_type="role",
            target_scope_id=role.id,
            operation="authorization.platform_role.denied",
        )
    if role.allowed_scope_type != ROLE_SCOPE_TENANT:
        authorization_denied(
            service._user_session,
            message=(
                f"Role '{role.name}' requires an explicit "
                f"{role.allowed_scope_type} scope."
            ),
            code="ROLE_SCOPE_REQUIRED",
            operation_label="revoke a scoped role",
            target_scope_type="role",
            target_scope_id=role.id,
            operation="authorization.resource_scope.denied",
        )
    user = service._require_user(user_id)
    _require_canonical_target_membership(
        service,
        user.id,
        tenant_id=tenant_id,
        operation="revoke",
    )
    binding = service._role_binding_repo.get_active_for_assignment(
        principal_id=user.id,
        role_id=role.id,
        tenant_id=tenant_id,
        actual_scope_type=ROLE_SCOPE_TENANT,
        actual_scope_id=None,
    )
    if binding is not None:
        service._require_role_governance_service().revoke_role_binding(
            binding.id
        )
    refresh_current_session_if_user(service, user.id)


def _require_customer_assignable_role(
    service: AuthService,
    role_name: str,
) -> str:
    normalized = normalize_role_name(role_name)
    if normalized in PLATFORM_ROLE_NAMES:
        authorization_denied(
            service._user_session,
            message=(
                f"Platform role '{normalized}' cannot be managed through a "
                "customer tenant."
            ),
            code="PLATFORM_ROLE_ASSIGNMENT_DENIED",
            operation_label="manage a customer tenant role",
            target_scope_type="role",
            target_scope_id=normalized,
            operation="authorization.permission_ceiling.denied",
        )
    if normalized in EXPLICIT_SCOPE_ROLE_NAMES:
        authorization_denied(
            service._user_session,
            message=f"Role '{normalized}' requires an explicit organization scope.",
            code="ROLE_SCOPE_REQUIRED",
            operation_label="manage a customer tenant role",
            target_scope_type="role",
            target_scope_id=normalized,
            operation="authorization.resource_scope.denied",
        )
    return normalized


def assign_customer_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(
        service._user_session,
        "auth.manage",
        operation_label="assign tenant role",
    )
    require_target_user_in_customer_tenant(
        service,
        user_id,
        operation_label="assign a tenant role",
        denial_code="ROLE_CROSS_TENANT_DENIED",
    )
    assign_role(service, user_id, _require_customer_assignable_role(service, role_name))


def revoke_customer_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(
        service._user_session,
        "auth.manage",
        operation_label="revoke tenant role",
    )
    require_target_user_in_customer_tenant(
        service,
        user_id,
        operation_label="revoke a tenant role",
        denial_code="ROLE_CROSS_TENANT_DENIED",
    )
    revoke_role(service, user_id, _require_customer_assignable_role(service, role_name))


__all__ = [
    "assign_customer_role",
    "assign_role",
    "revoke_customer_role",
    "revoke_role",
]
