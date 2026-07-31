from __future__ import annotations

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.auth.contracts import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserRoleRepository,
)
from src.core.platform.auth.domain import Role, UserAccount
from src.core.platform.auth.domain.role_binding import ROLE_SCOPE_PLATFORM


class AuthQueryMixin:
    # RBAC-TRANSITION-ONLY: Legacy role/permission reads are replaced by the
    # canonical principal query path before CANONICAL_AUTHORITATIVE.
    _user_repo: UserRepository
    _role_repo: RoleRepository
    _permission_repo: PermissionRepository
    _user_role_repo: UserRoleRepository
    _role_permission_repo: RolePermissionRepository

    def _canonical_platform_authority(self, user_id: str):
        return self._require_canonical_role_resolver().resolve(
            user_id,
            tenant_id=None,
            organization_id=None,
        )

    def _legacy_customer_role_ids(self, user_id: str) -> set[str]:
        role_ids: set[str] = set()
        for role_id in self._user_role_repo.list_role_ids(user_id):
            role = self._role_repo.get(role_id)
            if role is None or role.allowed_scope_type == ROLE_SCOPE_PLATFORM:
                continue
            role_ids.add(role_id)
        return role_ids

    def get_user_permissions(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        platform_authority = self._canonical_platform_authority(user_id)
        role_ids = self._legacy_customer_role_ids(user_id)
        permission_ids: set[str] = set()
        for role_id in role_ids:
            permission_ids.update(self._role_permission_repo.list_permission_ids(role_id))

        all_permissions = {perm.id: perm.code for perm in self._permission_repo.list_all()}
        return platform_authority.permissions.union(
            all_permissions[pid]
            for pid in permission_ids
            if pid in all_permissions
        )

    def has_permission(self, user_id: str, permission_code: str) -> bool:
        return permission_code in self.get_user_permissions(user_id)

    def get_user_role_names(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        platform_authority = self._canonical_platform_authority(user_id)
        role_ids = self._legacy_customer_role_ids(user_id)
        names: set[str] = set(platform_authority.role_names)
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
