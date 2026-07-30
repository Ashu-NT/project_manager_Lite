from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_any_permission, require_permission
from src.core.platform.auth.domain import Role, UserAccount, normalize_auth_username
from src.core.platform.common.exceptions import ValidationError

from .session_service import refresh_current_session_if_user
from .role_scope_policy import is_customer_assignable_role, is_platform_role
from .target_user_authorization import (
    is_platform_operator,
    require_actor_active_tenant,
    require_target_user_in_active_tenant,
)

if TYPE_CHECKING:
    from .auth_service import AuthService


def _enforce_user_tenant_boundary(service: AuthService, target_user_id: str, operation: str) -> None:
    require_target_user_in_active_tenant(
        service,
        target_user_id,
        operation_label=operation,
    )


def list_users(service: AuthService) -> list[UserAccount]:
    require_any_permission(
        service._user_session,
        ("auth.manage", "auth.read", "access.manage", "security.manage"),
        operation_label="list users",
    )
    if is_platform_operator(service):
        return service._user_repo.list_all()
    tenant_id = require_actor_active_tenant(
        service,
        operation_label="list tenant users",
    )
    return [
        user
        for user in service._user_repo.list_for_tenant(tenant_id)
        if not any(
            is_platform_role(role_name)
            for role_name in service.get_user_role_names(user.id)
        )
    ]


def list_roles(service: AuthService) -> list[Role]:
    require_any_permission(
        service._user_session,
        ("auth.manage", "auth.read"),
        operation_label="list roles",
    )
    if is_platform_operator(service):
        return service._role_repo.list_all()
    tenant_id = require_actor_active_tenant(
        service,
        operation_label="list tenant roles",
    )
    return service._role_repo.list_for_tenant(tenant_id)


def list_customer_assignable_roles(service: AuthService) -> list[Role]:
    require_any_permission(
        service._user_session,
        ("auth.manage", "auth.read"),
        operation_label="list tenant-assignable roles",
    )
    tenant_id = require_actor_active_tenant(
        service,
        operation_label="list tenant-assignable roles",
    )
    return [
        role
        for role in service._role_repo.list_for_tenant(tenant_id)
        if role.is_system
        and role.status == "active"
        and role.is_assignable
        and role.allowed_scope_type == "tenant"
        and is_customer_assignable_role(role.name)
    ]


def set_user_active(service: AuthService, user_id: str, is_active: bool) -> UserAccount:
    require_permission(service._user_session, "auth.manage", operation_label="set user active")
    _enforce_user_tenant_boundary(service, user_id, "set active status")
    user = service._require_user(user_id)
    user.is_active = bool(is_active)
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    record_audit_entry(
        service,
        operation="update",
        entity_type="user",
        entity_id=user.id,
        module="platform",
        severity="medium",
        field="is_active",
        metadata={"action": "user.set_active", "is_active": str(is_active)},
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def update_user_profile(
    service: AuthService,
    user_id: str,
    *,
    username: str | None = None,
    display_name: str | None = None,
    email: str | None = None,
) -> UserAccount:
    require_permission(service._user_session, "auth.manage", operation_label="update user profile")
    _enforce_user_tenant_boundary(service, user_id, "update profile")
    user = service._require_user(user_id)
    if username is not None:
        normalized = normalize_auth_username(username)
        existing = service._user_repo.get_by_username(normalized)
        if existing and existing.id != user.id:
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS")
        user.username = username
    if display_name is not None:
        user.display_name = display_name
    if email is not None:
        user.email = email
    user.updated_at = datetime.now(timezone.utc)
    try:
        service._user_repo.update(user)
        service._session.commit()
    except IntegrityError as exc:
        service._session.rollback()
        if "username" in str(exc).lower():
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS") from exc
        raise ValidationError(
            "Failed to update user due to data conflict.",
            code="USER_UPDATE_CONFLICT",
        ) from exc
    except Exception:
        service._session.rollback()
        raise
    record_audit_entry(
        service,
        operation="update",
        entity_type="user",
        entity_id=user.id,
        module="platform",
        severity="low",
        field="profile",
        metadata={"action": "user.update_profile"},
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


def unlock_user_account(service: AuthService, user_id: str) -> UserAccount:
    require_any_permission(
        service._user_session,
        ("auth.manage", "security.manage"),
        operation_label="unlock user account",
    )
    _enforce_user_tenant_boundary(service, user_id, "unlock account")
    user = service._require_user(user_id)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = datetime.now(timezone.utc)
    service._user_repo.update(user)
    service._session.commit()
    record_audit_entry(
        service,
        operation="update",
        entity_type="user",
        entity_id=user.id,
        module="platform",
        severity="medium",
        field="locked_until",
        metadata={"action": "user.unlock_account"},
    )
    domain_events.auth_changed.emit(user.id)
    refresh_current_session_if_user(service, user.id)
    return user


__all__ = [
    "list_customer_assignable_roles",
    "list_roles",
    "list_users",
    "set_user_active",
    "unlock_user_account",
    "update_user_profile",
]
