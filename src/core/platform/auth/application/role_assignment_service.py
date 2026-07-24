from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.auth.domain import UserRoleBinding
from src.core.platform.common.exceptions import BusinessRuleError

from .session_service import refresh_current_session_if_user
from .sod_enforcer import enforce_separation_of_duties

if TYPE_CHECKING:
    from .auth_service import AuthService

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
        raise BusinessRuleError(
            f"Cannot assign role '{role_name}': insufficient privilege level. (ROLE_PRIVILEGE_CEILING)",
            code="ROLE_PRIVILEGE_CEILING",
        )


# C-2: tenant-scope guard — target user must be a member of the caller's active tenant.
# Bypassed for admin / platform.admin callers and when no tenant repo is available.
def _enforce_tenant_membership(service: AuthService, target_user_id: str, operation: str) -> None:
    if service._user_tenant_repo is None:
        return
    if service._user_session is None:
        return
    principal = service._user_session.principal
    if principal is None:
        return
    if "admin" in principal.role_names or "platform.admin" in principal.permissions:
        return
    caller_tenant_id = str(service._user_session.active_tenant_id() or "").strip() or None
    if caller_tenant_id is None:
        return
    if not service._user_tenant_repo.is_active_member(target_user_id, caller_tenant_id):
        raise BusinessRuleError(
            f"Cannot {operation} role for a user outside the active tenant. (ROLE_CROSS_TENANT_DENIED)",
            code="ROLE_CROSS_TENANT_DENIED",
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
        service._user_role_repo.add(UserRoleBinding.create(user_id=user.id, role_id=role.id))
        service._session.commit()
        record_audit_entry(
            service,
            operation="permission_change",
            entity_type="user_role_binding",
            entity_id=user.id,
            module="platform",
            severity="medium",
            metadata={"action": "role.assign", "role_name": role_name, "user_id": user.id},
        )
        domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


def revoke_role(service: AuthService, user_id: str, role_name: str) -> None:
    require_permission(service._user_session, "auth.manage", operation_label="revoke role")
    user = service._require_user(user_id)
    _enforce_tenant_membership(service, user.id, "revoke")
    role = service._require_role_by_name(role_name)
    service._user_role_repo.delete(user.id, role.id)
    service._session.commit()
    record_audit_entry(
        service,
        operation="delete",
        entity_type="user_role_binding",
        entity_id=user.id,
        module="platform",
        severity="medium",
        metadata={"action": "role.revoke", "role_name": role_name, "user_id": user.id},
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)


__all__ = ["assign_role", "revoke_role"]
