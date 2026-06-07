from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.org.domain import Organization


@dataclass(frozen=True)
class TenantContext:
    organization_id: str
    organization: Organization


class TenantContextService:
    """Session-scoped organization context for tenant-owned business data.

    This service deliberately does not mutate ``Organization.is_active``. The
    database flag remains a compatibility/default selector; the runtime tenant
    selection belongs to the current user session.
    """

    def __init__(
        self,
        *,
        organization_repo: OrganizationRepository,
        user_session: UserSessionContext | None = None,
        fallback_to_global_active: bool = True,
    ) -> None:
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._fallback_to_global_active = bool(fallback_to_global_active)

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

        if self._fallback_to_global_active:
            organization = self._organization_repo.get_active()
            if organization is not None and self._can_access(organization.id):
                return organization
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

    def require_context(self, *, operation_label: str) -> TenantContext:
        organization = self.get_active_organization()
        if organization is None:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return TenantContext(organization_id=organization.id, organization=organization)

    def _session_organization_id(self) -> str | None:
        if self._user_session is None:
            return None
        return self._user_session.active_organization_id()

    def _can_access(self, organization_id: str) -> bool:
        if self._user_session is None or self._user_session.principal is None:
            return True
        return self._user_session.has_organization_access(organization_id)


__all__ = ["TenantContext", "TenantContextService"]
