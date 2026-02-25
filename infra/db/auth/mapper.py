from __future__ import annotations

from core.models import Permission, Role, RolePermissionBinding, UserAccount, UserRoleBinding
from infra.db.models import PermissionORM, RoleORM, RolePermissionORM, UserORM, UserRoleORM


def user_to_orm(user: UserAccount) -> UserORM:
    return UserORM(
        id=user.id,
        username=user.username,
        password_hash=user.password_hash,
        display_name=user.display_name,
        email=user.email,
        is_active=user.is_active,
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
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
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

