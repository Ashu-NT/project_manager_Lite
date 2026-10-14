"""Read-only user/role/authority queries shared by the Platform auth collaborators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.roles.canonical_role_resolver import (
    CanonicalRoleResolver,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.contract.repositories.security.auth import (
    RoleRepository,
    UserRepository,
)
from src.core.platform.domain.security.auth import Role, UserAccount

if TYPE_CHECKING:
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )


class AuthQueryHandler:
    def __init__(
        self,
        *,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        canonical_role_resolver: CanonicalRoleResolver | None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._role_repo = role_repo
        self._canonical_role_resolver = canonical_role_resolver
        self._tenant_context_service = tenant_context_service

    def require_canonical_role_resolver(self) -> CanonicalRoleResolver:
        if self._canonical_role_resolver is None:
            raise BusinessRuleError(
                "Canonical role-binding persistence is not configured.",
                code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
            )
        return self._canonical_role_resolver

    def canonical_platform_authority(self, user_id: str):
        return self.require_canonical_role_resolver().resolve(
            user_id,
            tenant_id=None,
            organization_id=None,
        )

    def canonical_current_authority(self, user_id: str):
        tenant_id = (
            self._tenant_context_service.get_active_tenant_id()
            if self._tenant_context_service is not None
            else None
        )
        return self.require_canonical_role_resolver().resolve_tenant_authority(
            user_id,
            tenant_id=tenant_id,
        )

    def get_user_permissions(self, user_id: str) -> set[str]:
        self.require_user(user_id)
        return set(self.canonical_current_authority(user_id).permissions)

    def has_permission(self, user_id: str, permission_code: str) -> bool:
        return permission_code in self.get_user_permissions(user_id)

    def get_user_role_names(self, user_id: str) -> set[str]:
        self.require_user(user_id)
        return set(self.canonical_current_authority(user_id).role_names)

    def require_role_by_name(self, role_name: str) -> Role:
        role = self._role_repo.get_by_name((role_name or "").strip().lower())
        if not role:
            raise NotFoundError("Role not found.", code="ROLE_NOT_FOUND")
        return role

    def require_tenant_role_by_name(
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

    def require_user(self, user_id: str) -> UserAccount:
        user = self._user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.", code="USER_NOT_FOUND")
        return user


__all__ = ["AuthQueryHandler"]
