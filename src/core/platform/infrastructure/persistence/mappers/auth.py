from __future__ import annotations

from src.core.platform.auth.domain import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
    UserRoleBinding,
)
from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.infrastructure.persistence.orm.auth import AuthSessionORM, PermissionORM, RoleORM, RolePermissionORM, UserORM, UserRoleORM


def user_to_orm(user: UserAccount) -> UserORM:
    return UserORM(
        id=user.id,
        username=user.username,
        password_hash=user.password_hash,
        display_name=user.display_name,
        email=user.email,
        identity_provider=getattr(user, "identity_provider", None),
        federated_subject=getattr(user, "federated_subject", None),
        mfa_secret=getattr(user, "mfa_secret", None),
        mfa_enabled=getattr(user, "mfa_enabled", False),
        session_timeout_minutes_override=getattr(user, "session_timeout_minutes_override", None),
        session_revision=getattr(user, "session_revision", 1),
        last_login_auth_method=getattr(user, "last_login_auth_method", None),
        last_login_device_label=getattr(user, "last_login_device_label", None),
        is_active=user.is_active,
        failed_login_attempts=getattr(user, "failed_login_attempts", 0),
        locked_until=getattr(user, "locked_until", None),
        last_login_at=getattr(user, "last_login_at", None),
        session_expires_at=getattr(user, "session_expires_at", None),
        password_changed_at=getattr(user, "password_changed_at", None),
        must_change_password=getattr(user, "must_change_password", False),
        created_at=user.created_at,
        updated_at=user.updated_at,
        version=getattr(user, "version", 1),
    )


def user_from_orm(obj: UserORM) -> UserAccount:
    return UserAccount(
        id=obj.id,
        username=obj.username,
        password_hash=obj.password_hash,
        display_name=obj.display_name,
        email=obj.email,
        identity_provider=getattr(obj, "identity_provider", None),
        federated_subject=getattr(obj, "federated_subject", None),
        mfa_secret=getattr(obj, "mfa_secret", None),
        mfa_enabled=getattr(obj, "mfa_enabled", False),
        session_timeout_minutes_override=getattr(obj, "session_timeout_minutes_override", None),
        session_revision=getattr(obj, "session_revision", 1),
        last_login_auth_method=getattr(obj, "last_login_auth_method", None),
        last_login_device_label=getattr(obj, "last_login_device_label", None),
        is_active=obj.is_active,
        failed_login_attempts=getattr(obj, "failed_login_attempts", 0),
        locked_until=ensure_utc_datetime(getattr(obj, "locked_until", None)),
        last_login_at=ensure_utc_datetime(getattr(obj, "last_login_at", None)),
        session_expires_at=ensure_utc_datetime(getattr(obj, "session_expires_at", None)),
        password_changed_at=ensure_utc_datetime(getattr(obj, "password_changed_at", None)),
        must_change_password=getattr(obj, "must_change_password", False),
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
        version=getattr(obj, "version", 1),
    )


def auth_session_to_orm(auth_session: AuthSession) -> AuthSessionORM:
    return AuthSessionORM(
        id=auth_session.id,
        user_id=auth_session.user_id,
        session_revision=auth_session.session_revision,
        auth_method=auth_session.auth_method,
        device_label=auth_session.device_label,
        issued_at=auth_session.issued_at,
        expires_at=auth_session.expires_at,
        last_validated_at=auth_session.last_validated_at,
        revoked_at=auth_session.revoked_at,
        created_at=auth_session.created_at,
        updated_at=auth_session.updated_at,
    )


def auth_session_from_orm(obj: AuthSessionORM) -> AuthSession:
    return AuthSession(
        id=obj.id,
        user_id=obj.user_id,
        session_revision=obj.session_revision,
        auth_method=obj.auth_method,
        device_label=obj.device_label,
        issued_at=ensure_utc_datetime(obj.issued_at),
        expires_at=ensure_utc_datetime(obj.expires_at),
        last_validated_at=ensure_utc_datetime(obj.last_validated_at),
        revoked_at=ensure_utc_datetime(obj.revoked_at),
        created_at=ensure_utc_datetime(obj.created_at),
        updated_at=ensure_utc_datetime(obj.updated_at),
    )


def role_to_orm(role: Role) -> RoleORM:
    return RoleORM(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
    )


def role_from_orm(obj: RoleORM) -> Role:
    return Role(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        is_system=obj.is_system,
    )


def permission_to_orm(permission: Permission) -> PermissionORM:
    return PermissionORM(
        id=permission.id,
        code=permission.code,
        description=permission.description,
    )


def permission_from_orm(obj: PermissionORM) -> Permission:
    return Permission(
        id=obj.id,
        code=obj.code,
        description=obj.description,
    )


def user_role_to_orm(binding: UserRoleBinding) -> UserRoleORM:
    return UserRoleORM(
        id=binding.id,
        user_id=binding.user_id,
        role_id=binding.role_id,
    )


def user_role_from_orm(obj: UserRoleORM) -> UserRoleBinding:
    return UserRoleBinding(
        id=obj.id,
        user_id=obj.user_id,
        role_id=obj.role_id,
    )


def role_permission_to_orm(binding: RolePermissionBinding) -> RolePermissionORM:
    return RolePermissionORM(
        id=binding.id,
        role_id=binding.role_id,
        permission_id=binding.permission_id,
    )


def role_permission_from_orm(obj: RolePermissionORM) -> RolePermissionBinding:
    return RolePermissionBinding(
        id=obj.id,
        role_id=obj.role_id,
        permission_id=obj.permission_id,
    )


__all__ = [
    "auth_session_from_orm",
    "auth_session_to_orm",
    "user_to_orm",
    "user_from_orm",
    "role_to_orm",
    "role_from_orm",
    "permission_to_orm",
    "permission_from_orm",
    "user_role_to_orm",
    "user_role_from_orm",
    "role_permission_to_orm",
    "role_permission_from_orm",
]
