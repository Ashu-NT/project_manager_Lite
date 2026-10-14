from __future__ import annotations

from src.core.platform.application.security.authorization.roles.tenant_role_authorization import (
    TenantRoleAuthorization,
)
from src.core.platform.contract.repositories.security.auth import RoleRepository
from src.core.platform.domain.security.auth import Role


class TenantRoleQueryHandler:
    """Authorized tenant-scoped custom-role reads without mutation dependencies."""

    def __init__(
        self, *, role_repo: RoleRepository, authorization: TenantRoleAuthorization
    ) -> None:
        self._role_repo = role_repo
        self._authorization = authorization

    def list_custom_roles(self) -> list[Role]:
        _, tenant_id = self._authorization.require_role_administrator(
            operation_label="list tenant custom roles"
        )
        return [
            role
            for role in self._role_repo.list_for_tenant(
                tenant_id,
                include_system=False,
            )
            if role.status != "retired"
        ]
