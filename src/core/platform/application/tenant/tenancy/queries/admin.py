"""Platform tenant catalog and accessibility queries."""

from __future__ import annotations

import src.core.platform.application.tenant.tenancy.mappers.tenant as response_mapper
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.dto.responses.tenant import TenantDto
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    TenantRepository,
    UserTenantMembershipRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.tenant.tenancy.tenant import (
    Tenant,
)


class TenantAdminQueryHandler:
    """Platform catalog and current-user accessible tenant queries."""

    def __init__(
        self,
        *,
        tenant_repo: TenantRepository,
        user_tenant_repo: UserTenantMembershipRepository,
        user_session: UserSessionContext,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._user_tenant_repo = user_tenant_repo
        self._user_session = user_session

    def require_tenant(self, tenant_id: str) -> Tenant:
        normalized = str(tenant_id or "").strip()
        tenant = self._tenant_repo.get(normalized) if normalized else None
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        return tenant

    def _current_user_id(self) -> str | None:
        principal = getattr(self._user_session, "principal", None)
        if principal is None:
            return None
        return str(getattr(principal, "user_id", "") or "").strip() or None

    def get_tenant(self, tenant_id: str) -> Tenant:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="get tenant",
        )
        return self.require_tenant(tenant_id)

    def list_tenants(self, *, active_only: bool | None = None) -> list[Tenant]:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="list tenants",
        )
        return self._tenant_repo.list_all(active_only=active_only)

    def list_accessible_tenants(self) -> list[TenantDto]:
        """Return tenants the current user can switch to.

        No permission guard â€” listing one's own memberships is always allowed.
        Platform.admin and admin: all tenants (including suspended/archived, so
        the UI can show their status). Regular users: only active (non-suspended,
        non-archived) tenants where an active user_tenants membership exists.
        """
        user_id = self._current_user_id()
        if not user_id:
            return []
        principal = getattr(self._user_session, "principal", None)
        if principal is not None:
            is_admin = "admin" in getattr(principal, "role_names", frozenset())
            is_platform_admin = "platform.admin" in getattr(
                principal, "permissions", frozenset()
            )
            if is_admin or is_platform_admin:
                return [response_mapper.serialize_tenant(row) for row in (self._tenant_repo.list_all(active_only=None))]
        tenant_ids = self._user_tenant_repo.list_tenant_ids_for_user(user_id)
        tenants: list[Tenant] = []
        for tid in tenant_ids:
            tenant = self._tenant_repo.get(tid)
            if tenant is not None and tenant.is_active:
                tenants.append(tenant)
        return [response_mapper.serialize_tenant(row) for row in (tenants)]

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
