from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization
from src.core.platform.tenancy.contracts import TenantRepository
from src.core.platform.tenancy.domain.tenant import Tenant


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant: Tenant
    organization_id: str | None
    organization: Organization | None


class TenantContextService:
    """Session-scoped tenant + organization context for multi-tenant business data.

    Hierarchy: Tenant → Organization → Site → Department.
    A session may have an active tenant and an active organization within that tenant.
    """

    def __init__(
        self,
        *,
        tenant_repo: TenantRepository,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None = None,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._organization_repo = organization_repo
        self._user_session = user_session

    # ------------------------------------------------------------------
    # Tenant resolution
    # ------------------------------------------------------------------

    def get_active_tenant_id(self) -> str | None:
        tenant = self.get_active_tenant()
        return tenant.id if tenant is not None else None

    def require_active_tenant_id(self, *, operation_label: str) -> str:
        tenant = self.get_active_tenant()
        if tenant is None:
            raise BusinessRuleError(
                f"Active tenant context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant.id

    def get_active_tenant(self) -> Tenant | None:
        tenant_id = self._session_tenant_id()
        if tenant_id:
            tenant = self._tenant_repo.get(tenant_id)
            if tenant is not None and tenant.is_active:
                return tenant
        # Fall back to the default (single-tenant desktop mode)
        return self._tenant_repo.get_default()

    def set_active_tenant(self, tenant_id: str) -> Tenant:
        normalized_id = str(tenant_id or "").strip()
        if not normalized_id:
            raise BusinessRuleError("Tenant is required.", code="TENANT_CONTEXT_REQUIRED")
        tenant = self._tenant_repo.get(normalized_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if not tenant.is_active:
            raise BusinessRuleError(
                "Cannot switch to an inactive tenant.",
                code="TENANT_INACTIVE",
            )
        if self._user_session is not None:
            self._user_session.set_active_tenant_id(tenant.id)
        return tenant

    # ------------------------------------------------------------------
    # Organization resolution (within the active tenant)
    # ------------------------------------------------------------------

    def get_active_organization_id(self) -> str | None:
        organization = self.get_active_organization()
        return organization.id if organization is not None else None

    def require_active_organization_id(self, *, operation_label: str) -> str:
        organization = self.get_active_organization()
        if organization is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return organization.id

    def get_active_organization(self) -> Organization | None:
        organization_id = self._session_organization_id()
        if organization_id:
            organization = self._organization_repo.get(organization_id)
            if organization is not None and self._can_access(organization.id):
                return organization
            if self._user_session is not None:
                self._user_session.set_active_organization_id(None)
        return None

    def set_active_organization(self, organization_id: str) -> Organization:
        normalized_id = str(organization_id or "").strip()
        if not normalized_id:
            raise BusinessRuleError(
                "Organization is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        organization = self._organization_repo.get(normalized_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")
        if not getattr(organization, "is_active", True):
            raise BusinessRuleError(
                "Cannot switch to an inactive organization.",
                code="ORGANIZATION_INACTIVE",
            )
        if not self._can_access(organization.id):
            raise BusinessRuleError(
                "Permission denied for organization context.",
                code="PERMISSION_DENIED",
            )
        if self._user_session is not None:
            self._user_session.set_active_organization_id(organization.id)
        return organization

    # ------------------------------------------------------------------
    # Full context
    # ------------------------------------------------------------------

    def require_context(self, *, operation_label: str) -> TenantContext:
        tenant = self.get_active_tenant()
        if tenant is None:
            raise BusinessRuleError(
                f"Active tenant context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        organization = self.get_active_organization()
        return TenantContext(
            tenant_id=tenant.id,
            tenant=tenant,
            organization_id=organization.id if organization is not None else None,
            organization=organization,
        )

    def require_organization_context(self, *, operation_label: str) -> TenantContext:
        """Require both tenant and organization to be set."""
        ctx = self.require_context(operation_label=operation_label)
        if ctx.organization_id is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return ctx

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_tenant_id(self) -> str | None:
        if self._user_session is None:
            return None
        return getattr(self._user_session, "active_tenant_id", lambda: None)()

    def _session_organization_id(self) -> str | None:
        if self._user_session is None:
            return None
        return self._user_session.active_organization_id()

    def _can_access(self, organization_id: str) -> bool:
        if self._user_session is None:
            return True
        principal = self._user_session.principal
        if principal is None:
            return True
        if "admin" in getattr(principal, "role_names", frozenset()):
            return True
        normalized_organization_id = str(organization_id or "").strip()
        if not normalized_organization_id:
            return False
        organization_scopes = dict((principal.scoped_access or {}).get("organization", {}))
        return bool(organization_scopes) and normalized_organization_id in organization_scopes


__all__ = ["TenantContext", "TenantContextService"]
