from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import (
    authorization_denied,
    require_permission,
)
from src.core.platform.auth.domain import UserRoleBinding

from .session_service import refresh_current_session_if_user
from .security_audit import add_atomic_security_audit
from .sod_enforcer import enforce_separation_of_duties
from .role_scope_policy import (
    EXPLICIT_SCOPE_ROLE_NAMES,
    PLATFORM_ROLE_NAMES,
    normalize_role_name,
)
from .target_user_authorization import (
    require_target_user_in_active_tenant,
    require_target_user_in_customer_tenant,
)

if TYPE_CHECKING:
    from .auth_service import AuthService

# RBAC-TRANSITION-ONLY: This module mutates legacy user_roles. Replace callers
# with canonical governance, then remove after CANONICAL_ONLY observation.

# C-1: privilege ceiling — roles ranked higher than the caller cannot be assigned.
# admin (100) > tenant_admin (80) > org_admin (70) > everything else (10).
_PRIVILEGE_RANK: dict[str, int] = {
    "admin": 100,
    "tenant_admin": 80,
    "org_admin": 70,
}
_DEFAULT_RANK = 10


def _caller_max_rank(service: AuthService) -> int:
    if service._user_session is None:
        return 0
    principal = service._user_session.principal
    if principal is None:
        return 0
    return max(
        (_PRIVILEGE_RANK.get(r, _DEFAULT_RANK) for r in principal.role_names),
        default=0,
    )


def _role_rank(role_name: str) -> int:
    return _PRIVILEGE_RANK.get(str(role_name or "").strip().lower(), _DEFAULT_RANK)


def _enforce_privilege_ceiling(service: AuthService, role_name: str) -> None:
    caller_rank = _caller_max_rank(service)
    if caller_rank >= 100:
        return  # admin bypasses ceiling
    if _role_rank(role_name) >= caller_rank:
        authorization_denied(
            service._user_session,
            message=(
                f"Cannot assign role '{role_name}': insufficient privilege "
                "level. (ROLE_PRIVILEGE_CEILING)"
            ),
            code="ROLE_PRIVILEGE_CEILING",
            operation_label="assign role",
            target_scope_type="role",
            target_scope_id=role_name,
            operation="authorization.permission_ceiling.denied",
        )


# C-2: tenant-scope guard — target user must be a member of the caller's active tenant.
# Bypassed for admin / platform.admin callers and when no tenant repo is available.
def _enforce_tenant_membership(service: AuthService, target_user_id: str, operation: str) -> None:
    require_target_user_in_active_tenant(
        service,
        target_user_id,
        operation_label=f"{operation} role",
        denial_code="ROLE_CROSS_TENANT_DENIED",
    )


def assign_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="assign role")
    _enforce_privilege_ceiling(service, role_name)
    user = service._require_user(user_id)
    _enforce_tenant_membership(service, user.id, "assign")
    existing_role_names = service.get_user_role_names(user.id)
    enforce_separation_of_duties(service, tuple(existing_role_names) + (role_name,))
    role = service._require_role_by_name(role_name)
    if not service._user_role_repo.exists(user.id, role.id):
        try:
            service._user_role_repo.add(
                UserRoleBinding.create(
                    user_id=user.id,
                    role_id=role.id,
                )
            )
            add_atomic_security_audit(
                service,
                operation="permission_change",
                entity_type="user_role_binding",
                entity_id=user.id,
                action="role.assign",
                severity="high",
                field="role",
                new_value=role.name,
                metadata={
                    "role_name": role.name,
                    "target_user_id": user.id,
                },
            )
            service._session.commit()
        except Exception:
            service._session.rollback()
            raise
        domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


def revoke_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="revoke role")
    user = service._require_user(user_id)
    _enforce_tenant_membership(service, user.id, "revoke")
    role = service._require_role_by_name(role_name)
    if service._user_role_repo.exists(user.id, role.id):
        try:
            service._user_role_repo.delete(user.id, role.id)
            add_atomic_security_audit(
                service,
                operation="delete",
                entity_type="user_role_binding",
                entity_id=user.id,
                action="role.revoke",
                severity="high",
                field="role",
                old_value=role.name,
                metadata={
                    "role_name": role.name,
                    "target_user_id": user.id,
                },
            )
            service._session.commit()
        except Exception:
            service._session.rollback()
            raise
        domain_events.auth_changed.emit(user.id)
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
    assign_role(
        service,
        user_id,
        _require_customer_assignable_role(service, role_name),
    )


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
    revoke_role(
        service,
        user_id,
        _require_customer_assignable_role(service, role_name),
    )


__all__ = [
    "assign_customer_role",
    "assign_role",
    "revoke_customer_role",
    "revoke_role",
]
