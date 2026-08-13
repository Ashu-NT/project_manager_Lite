from __future__ import annotations

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.security.auth import (
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth import Role, UserAccount


class AuthQueryMixin:
    _user_repo: UserRepository
    _role_repo: RoleRepository
    _permission_repo: PermissionRepository
    _role_permission_repo: RolePermissionRepository

    def _canonical_platform_authority(self, user_id: str):
        return self._require_canonical_role_resolver().resolve(
            user_id,
            tenant_id=None,
            organization_id=None,
        )

    def _canonical_current_authority(self, user_id: str):
        tenant_id = (
            self._tenant_context_service.get_active_tenant_id()
            if self._tenant_context_service is not None
            else None
        )
        return self._require_canonical_role_resolver().resolve_tenant_authority(
            user_id,
            tenant_id=tenant_id,
        )

    def get_user_permissions(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        return set(self._canonical_current_authority(user_id).permissions)

    def has_permission(self, user_id: str, permission_code: str) -> bool:
        return permission_code in self.get_user_permissions(user_id)

    def get_user_role_names(self, user_id: str) -> set[str]:
        self._require_user(user_id)
        return set(self._canonical_current_authority(user_id).role_names)

    def _require_role_by_name(self, role_name: str) -> Role:
        role = self._role_repo.get_by_name((role_name or "").strip().lower())
        if not role:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def _require_tenant_role_by_name(
        self,
        tenant_id: str,
        role_name: str,
    ) -> Role:
        role = self._role_repo.get_for_tenant_by_name(
            tenant_id,
            (role_name or "").strip().lower(),
        )
        if not role:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def _require_user(self, user_id: str) -> UserAccount:
        user = self._user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user
