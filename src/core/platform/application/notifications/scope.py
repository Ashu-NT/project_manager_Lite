from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    UserTenantMembershipRepository,
)
from src.core.platform.domain.security.auth.session import (
    UserSessionContext,
    UserSessionPrincipal,
)


class NotificationRecipientScope:
    """Resolve personal scope anew on each operation, including membership revocation."""

    def __init__(self, *, user_session: UserSessionContext | None = None, memberships: UserTenantMembershipRepository | None = None) -> None:
        self._user_session = user_session
        self._memberships = memberships

    def scope(self, user_id: str) -> tuple[str | None, str | None]:
        if self._user_session is None:
            return None, None
        tenant_id = self._user_session.stored_active_tenant_id()
        if tenant_id and self._memberships is not None:
            active = any(
                membership.tenant_id == tenant_id and membership.status == "active"
                for membership in self._memberships.list_memberships_for_user(user_id)
            )
            if not active:
                return None, None
        return tenant_id, self._user_session.stored_active_organization_id() if tenant_id else None

    def require_principal(self) -> UserSessionPrincipal:
        principal = self._user_session.principal if self._user_session is not None else None
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required to view notifications.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal
