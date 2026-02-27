from __future__ import annotations

from core.exceptions import NotFoundError
from core.interfaces import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from core.models import Role, UserAccount


class AuthQueryMixin:
    _user_repo: UserRepository
    _role_repo: RoleRepository
    _permission_repo: PermissionRepository
    _user_role_repo: UserRoleRepository
    _role_permission_repo: RolePermissionRepository

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
