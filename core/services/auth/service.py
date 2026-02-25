from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from core.exceptions import NotFoundError, ValidationError
from core.interfaces import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from core.models import Permission, Role, RolePermissionBinding, UserAccount, UserRoleBinding
from core.services.auth.passwords import hash_password, verify_password
from core.services.auth.policy import DEFAULT_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from core.services.auth.session import UserSessionPrincipal


class AuthService:
    def __init__(
        self,
        session: Session,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        user_role_repo: UserRoleRepository,
        role_permission_repo: RolePermissionRepository,
    ):
        self._session: Session = session
        self._user_repo: UserRepository = user_repo
        self._role_repo: RoleRepository = role_repo
        self._permission_repo: PermissionRepository = permission_repo
        self._user_role_repo: UserRoleRepository = user_role_repo
        self._role_permission_repo: RolePermissionRepository = role_permission_repo

    def bootstrap_defaults(self) -> UserAccount:
        self._ensure_default_permissions()
        self._session.flush()
        role_map = self._ensure_default_roles()
        self._session.flush()
        self._ensure_role_permissions(role_map)
        self._session.flush()

        admin_username = (os.getenv("PM_ADMIN_USERNAME", "admin").strip() or "admin").lower()
        admin_password = os.getenv("PM_ADMIN_PASSWORD", "ChangeMe123!")
        admin = self._user_repo.get_by_username(admin_username)
        if admin is None:
            admin = self.register_user(
                username=admin_username,
                raw_password=admin_password,
                display_name="Administrator",
                role_names=["admin"],
                commit=False,
            )
        else:
            admin_role = role_map.get("admin")
            if admin_role and not self._user_role_repo.exists(admin.id, admin_role.id):
                self._user_role_repo.add(UserRoleBinding.create(user_id=admin.id, role_id=admin_role.id))

        self._session.commit()
        return admin

    def register_user(
        self,
        username: str,
        raw_password: str,
        display_name: str | None = None,
        email: str | None = None,
        is_active: bool = True,
        role_names: Iterable[str] | None = None,
        *,
        commit: bool = True,
    ) -> UserAccount:
        normalized = (username or "").strip().lower()
        if not normalized:
            raise ValidationError("Username is required.", code="USERNAME_REQUIRED")
        self._validate_password(raw_password)
        if self._user_repo.get_by_username(normalized):
            raise ValidationError("Username already exists.", code="USERNAME_EXISTS")

        user = UserAccount.create(
            username=normalized,
            password_hash=hash_password(raw_password),
            display_name=(display_name or "").strip() or None,
            email=(email or "").strip() or None,
            is_active=is_active,
        )
        self._user_repo.add(user)
        self._assign_roles_for_user(user.id, role_names or ("viewer",))

        if commit:
            self._session.commit()
        return user

    def authenticate(self, username: str, raw_password: str) -> UserAccount:
        normalized = (username or "").strip().lower()
        user = self._user_repo.get_by_username(normalized)
        if not user or not user.is_active:
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        if not verify_password(raw_password, user.password_hash):
            raise ValidationError("Invalid credentials.", code="AUTH_FAILED")
        return user

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        user = self._require_user(user_id)
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect.", code="AUTH_FAILED")

        self._validate_password(new_password)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self._user_repo.update(user)
        self._session.commit()

    def assign_role(self, user_id: str, role_name: str) -> None:
        user = self._require_user(user_id)
        role = self._require_role_by_name(role_name)
        if not self._user_role_repo.exists(user.id, role.id):
            self._user_role_repo.add(UserRoleBinding.create(user_id=user.id, role_id=role.id))
            self._session.commit()

    def revoke_role(self, user_id: str, role_name: str) -> None:
        user = self._require_user(user_id)
        role = self._require_role_by_name(role_name)
        self._user_role_repo.delete(user.id, role.id)
        self._session.commit()

    def get_user_permissions(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        role_ids = self._user_role_repo.list_role_ids(user_id)
        permission_ids: set[str] = set()
        for role_id in role_ids:
            permission_ids.update(self._role_permission_repo.list_permission_ids(role_id))

        all_permissions = {perm.id: perm.code for perm in self._permission_repo.list_all()}
        return {all_permissions[pid] for pid in permission_ids if pid in all_permissions}

    def has_permission(self, user_id: str, permission_code: str) -> bool:
        return permission_code in self.get_user_permissions(user_id)

    def get_user_role_names(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        role_ids = self._user_role_repo.list_role_ids(user_id)
        names: set[str] = set()
        for role_id in role_ids:
            role = self._role_repo.get(role_id)
            if role:
                names.add(role.name)
        return names

    def build_principal(self, user: UserAccount) -> UserSessionPrincipal:
        return UserSessionPrincipal(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            role_names=frozenset(self.get_user_role_names(user.id)),
            permissions=frozenset(self.get_user_permissions(user.id)),
        )

    def _assign_roles_for_user(self, user_id: str, role_names: Iterable[str]) -> None:
        for role_name in role_names:
            role = self._require_role_by_name(role_name)
            if not self._user_role_repo.exists(user_id, role.id):
                self._user_role_repo.add(UserRoleBinding.create(user_id=user_id, role_id=role.id))

    def _ensure_default_permissions(self) -> None:
        for code, description in DEFAULT_PERMISSIONS.items():
            if self._permission_repo.get_by_code(code) is None:
                self._permission_repo.add(Permission.create(code=code, description=description))

    def _ensure_default_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            role = self._role_repo.get_by_name(role_name)
            if role is None:
                role = Role.create(name=role_name, description=f"System role: {role_name}", is_system=True)
                self._role_repo.add(role)
            roles[role_name] = role
        return roles

    def _ensure_role_permissions(self, role_map: dict[str, Role]) -> None:
        permission_map = {p.code: p.id for p in self._permission_repo.list_all()}
        for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = role_map.get(role_name)
            if not role:
                continue
            for code in permission_codes:
                permission_id = permission_map.get(code)
                if not permission_id:
                    continue
                if not self._role_permission_repo.exists(role.id, permission_id):
                    self._role_permission_repo.add(
                        RolePermissionBinding.create(
                            role_id=role.id,
                            permission_id=permission_id,
                        )
                    )

    def _require_role_by_name(self, role_name: str) -> Role:
        role = self._role_repo.get_by_name((role_name or "").strip().lower())
        if not role:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def _require_user(self, user_id: str) -> UserAccount:
        user = self._user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password or "") < 8:
            raise ValidationError("Password must be at least 8 characters.", code="WEAK_PASSWORD")


__all__ = ["AuthService"]
