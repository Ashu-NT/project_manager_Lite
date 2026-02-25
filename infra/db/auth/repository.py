from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.interfaces import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from core.models import Permission, Role, RolePermissionBinding, UserAccount, UserRoleBinding
from infra.db.auth.mapper import (
    permission_from_orm,
    permission_to_orm,
    role_from_orm,
    role_permission_to_orm,
    role_to_orm,
    user_from_orm,
    user_role_to_orm,
    user_to_orm,
)
from infra.db.models import PermissionORM, RoleORM, RolePermissionORM, UserORM, UserRoleORM
from infra.db.optimistic import update_with_version_check


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, user: UserAccount) -> None:
        self.session.add(user_to_orm(user))

    def update(self, user: UserAccount) -> None:
        user.version = update_with_version_check(
            self.session,
            UserORM,
            user.id,
            getattr(user, "version", 1),
            {
                "username": user.username,
                "password_hash": user.password_hash,
                "display_name": user.display_name,
                "email": user.email,
                "is_active": user.is_active,
                "updated_at": user.updated_at,
            },
            not_found_message="User not found.",
            stale_message="User account was updated by another user.",
        )

    def get(self, user_id: str) -> Optional[UserAccount]:
        obj = self.session.get(UserORM, user_id)
        return user_from_orm(obj) if obj else None

    def get_by_username(self, username: str) -> Optional[UserAccount]:
        stmt = select(UserORM).where(UserORM.username == username)
        obj = self.session.execute(stmt).scalars().first()
        return user_from_orm(obj) if obj else None

    def list_all(self) -> List[UserAccount]:
        rows = self.session.execute(select(UserORM)).scalars().all()
        return [user_from_orm(row) for row in rows]


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, role: Role) -> None:
        self.session.add(role_to_orm(role))

    def get(self, role_id: str) -> Optional[Role]:
        obj = self.session.get(RoleORM, role_id)
        return role_from_orm(obj) if obj else None

    def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(RoleORM).where(RoleORM.name == name)
        obj = self.session.execute(stmt).scalars().first()
        return role_from_orm(obj) if obj else None

    def list_all(self) -> List[Role]:
        rows = self.session.execute(select(RoleORM)).scalars().all()
        return [role_from_orm(row) for row in rows]


class SqlAlchemyPermissionRepository(PermissionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, permission: Permission) -> None:
        self.session.add(permission_to_orm(permission))

    def get(self, permission_id: str) -> Optional[Permission]:
        obj = self.session.get(PermissionORM, permission_id)
        return permission_from_orm(obj) if obj else None

    def get_by_code(self, code: str) -> Optional[Permission]:
        stmt = select(PermissionORM).where(PermissionORM.code == code)
        obj = self.session.execute(stmt).scalars().first()
        return permission_from_orm(obj) if obj else None

    def list_all(self) -> List[Permission]:
        rows = self.session.execute(select(PermissionORM)).scalars().all()
        return [permission_from_orm(row) for row in rows]


class SqlAlchemyUserRoleRepository(UserRoleRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, binding: UserRoleBinding) -> None:
        if self.exists(binding.user_id, binding.role_id):
            return
        self.session.add(user_role_to_orm(binding))

    def delete(self, user_id: str, role_id: str) -> None:
        self.session.query(UserRoleORM).filter_by(user_id=user_id, role_id=role_id).delete()

    def exists(self, user_id: str, role_id: str) -> bool:
        stmt = select(UserRoleORM.id).where(
            UserRoleORM.user_id == user_id,
            UserRoleORM.role_id == role_id,
        )
        return self.session.execute(stmt).first() is not None

    def list_role_ids(self, user_id: str) -> List[str]:
        stmt = select(UserRoleORM.role_id).where(UserRoleORM.user_id == user_id)
        return list(self.session.execute(stmt).scalars().all())


class SqlAlchemyRolePermissionRepository(RolePermissionRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, binding: RolePermissionBinding) -> None:
        if self.exists(binding.role_id, binding.permission_id):
            return
        self.session.add(role_permission_to_orm(binding))

    def delete(self, role_id: str, permission_id: str) -> None:
        self.session.query(RolePermissionORM).filter_by(
            role_id=role_id,
            permission_id=permission_id,
        ).delete()

    def exists(self, role_id: str, permission_id: str) -> bool:
        stmt = select(RolePermissionORM.id).where(
            RolePermissionORM.role_id == role_id,
            RolePermissionORM.permission_id == permission_id,
        )
        return self.session.execute(stmt).first() is not None

    def list_permission_ids(self, role_id: str) -> List[str]:
        stmt = select(RolePermissionORM.permission_id).where(RolePermissionORM.role_id == role_id)
        return list(self.session.execute(stmt).scalars().all())


__all__ = [
    "SqlAlchemyUserRepository",
    "SqlAlchemyRoleRepository",
    "SqlAlchemyPermissionRepository",
    "SqlAlchemyUserRoleRepository",
    "SqlAlchemyRolePermissionRepository",
]

