from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import record_authorization_denial
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    DomainError,
    NotFoundError,
)
from src.core.platform.contract.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.contract.tenant.tenancy.contracts import TenantRepository, UserTenantMembershipRepository
from src.core.platform.application.tenant.tenancy.context_policy import (
    LocalSingleTenantContextPolicy,
    TenancyMode,
    TenantContextPolicy,
)
from src.core.platform.domain.tenant.tenancy.tenant import Tenant

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionPrincipal


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant: Tenant
    organization_id: str | None
    organization: Organization | None


@dataclass(frozen=True)
class ActiveScopeIds:
    """Lightweight, immutable (tenant_id, organization_id) pair for repository-level SQL
    predicates. Carries IDs only - never ORM/domain entities - so it cannot go stale in the
    session-coupling sense `TenantContext.tenant`/`.organization` can."""

    tenant_id: str
    organization_id: str


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
        user_tenant_repo: UserTenantMembershipRepository | None = None,
        context_policy: TenantContextPolicy | None = None,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._user_tenant_repo = user_tenant_repo
        self._context_policy = context_policy or LocalSingleTenantContextPolicy()
        self._principal_rebuilder: (
            Callable[[str, str | None], "UserSessionPrincipal"] | None
        ) = None
        self._context_switch_committer: (
            Callable[["UserSessionPrincipal", str], None] | None
        ) = None

    def set_principal_rebuilder(
        self,
        rebuilder: Callable[[str, str | None], "UserSessionPrincipal"] | None,
    ) -> None:
        self._principal_rebuilder = rebuilder

    def set_context_switch_committer(
        self,
        committer: Callable[["UserSessionPrincipal", str], None] | None,
    ) -> None:
        self._context_switch_committer = committer

    @property
    def tenancy_mode(self) -> TenancyMode:
        return self._context_policy.mode

    def initial_tenant_id_for_user(self, user_id: str) -> str | None:
        membership_ids = (
            self._user_tenant_repo.list_tenant_ids_for_user(user_id)
            if self._user_tenant_repo is not None
            else []
        )
        if len(membership_ids) == 1:
            return membership_ids[0]
        if (
            not membership_ids
            and self._context_policy.mode is TenancyMode.LOCAL_SINGLE_TENANT
        ):
            tenant = self._tenant_repo.get_default()
            return tenant.id if tenant is not None and tenant.is_active else None
        return None

    def initial_organization_id_for_tenant(self, tenant_id: str) -> str | None:
        organizations = self._organization_repo.list_for_tenant(
            tenant_id,
            active_only=True,
        )
        return organizations[0].id if len(organizations) == 1 else None

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
        return self._context_policy.resolve_active_tenant(
            session_tenant_id=self._session_tenant_id(),
            tenant_repo=self._tenant_repo,
        )

    def set_active_tenant(self, tenant_id: str) -> Tenant:
        if self._context_policy.mode is TenancyMode.SAAS:
            return self.switch_to_tenant(tenant_id)
        if (
            self._user_session is not None
            and self._user_session.principal is not None
            and self._principal_rebuilder is not None
        ):
            return self.switch_to_tenant(tenant_id)
        try:
            tenant = self._require_available_tenant(tenant_id)
            self._require_current_principal_tenant_access(tenant.id)
            if self._user_session is not None:
                self._user_session.set_active_tenant_id(tenant.id)
            return tenant
        except DomainError as exc:
            self._record_context_switch_denial(
                switch_type="tenant",
                target_scope_id=tenant_id,
                error=exc,
            )
            raise

    def _require_available_tenant(self, tenant_id: str) -> Tenant:
        normalized_id = str(tenant_id or "").strip()
        if not normalized_id:
            raise BusinessRuleError("Tenant is required.", code="TENANT_CONTEXT_REQUIRED")
        tenant = self._tenant_repo.get(normalized_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.", code="TENANT_NOT_FOUND")
        if tenant.tenant_status == "suspended":
            raise BusinessRuleError(
                "Cannot switch to a suspended tenant.",
                code="TENANT_SUSPENDED",
            )
        if tenant.tenant_status == "archived":
            raise BusinessRuleError(
                "Cannot switch to an archived tenant.",
                code="TENANT_ARCHIVED",
            )
        if not tenant.is_active:
            raise BusinessRuleError(
                "Cannot switch to an inactive tenant.",
                code="TENANT_INACTIVE",
            )
        return tenant

    def _require_current_principal_tenant_access(self, tenant_id: str) -> None:
        if self._user_tenant_repo is None or self._user_session is None:
            return
        principal = self._user_session.principal
        if principal is None:
            return
        is_admin = "admin" in getattr(principal, "role_names", frozenset())
        is_platform_admin = "platform.admin" in getattr(
            principal,
            "permissions",
            frozenset(),
        )
        if is_admin or is_platform_admin:
            return
        user_id = str(getattr(principal, "user_id", "") or "").strip()
        if user_id and not self._user_tenant_repo.is_active_member(user_id, tenant_id):
            raise BusinessRuleError(
                "User does not have access to this tenant.",
                code="TENANT_ACCESS_DENIED",
            )

    def validate_principal_context(
        self,
        *,
        user_id: str,
        is_platform_operator: bool,
        tenant_id: str | None,
        organization_id: str | None,
    ) -> tuple[str | None, str | None]:
        """Validate a target context without mutating the current session."""
        normalized_tenant_id = str(tenant_id or "").strip() or None
        normalized_organization_id = str(organization_id or "").strip() or None
        if normalized_tenant_id is None:
            if normalized_organization_id is not None:
                raise BusinessRuleError(
                    "Organization context requires an explicit tenant.",
                    code="TENANT_CONTEXT_REQUIRED",
                )
            return None, None

        tenant = self._require_available_tenant(normalized_tenant_id)
        if not is_platform_operator:
            if self._user_tenant_repo is None:
                raise BusinessRuleError(
                    "Tenant membership validation is not configured.",
                    code="AUTHORIZATION_CONTEXT_REQUIRED",
                )
            is_active_member = self._user_tenant_repo.is_active_member(
                user_id,
                tenant.id,
            )
            default_tenant = (
                self._tenant_repo.get_default()
                if self._context_policy.mode is TenancyMode.LOCAL_SINGLE_TENANT
                else None
            )
            local_default_allowed = (
                default_tenant is not None and default_tenant.id == tenant.id
            )
            if not is_active_member and not local_default_allowed:
                raise BusinessRuleError(
                    "User does not have access to this tenant.",
                    code="TENANT_ACCESS_DENIED",
                )

        if normalized_organization_id is None:
            return tenant.id, None
        organization = self._organization_repo.get_for_tenant(
            normalized_organization_id,
            tenant.id,
        )
        if organization is None:
            raise BusinessRuleError(
                "Organization does not belong to the requested tenant.",
                code="ORGANIZATION_TENANT_MISMATCH",
            )
        if not getattr(organization, "is_active", True):
            raise BusinessRuleError(
                "Cannot restore an inactive organization.",
                code="ORGANIZATION_INACTIVE",
            )
        return tenant.id, organization.id

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
            if organization is not None and self._can_access(organization):
                return organization
            if self._user_session is not None:
                self._user_session.set_active_organization_id(None)
        return None

    def set_active_organization(self, organization_id: str) -> Organization:
        try:
            return self._set_active_organization(organization_id)
        except DomainError as exc:
            self._record_context_switch_denial(
                switch_type="organization",
                target_scope_id=organization_id,
                error=exc,
            )
            raise

    def _set_active_organization(self, organization_id: str) -> Organization:
        if self._context_policy.mode is TenancyMode.SAAS and (
            self._user_session is None
            or self._user_session.principal is None
        ):
            raise BusinessRuleError(
                "Authentication is required to switch organizations.",
                code="AUTHENTICATION_REQUIRED",
            )
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
        if not self._can_access(organization):
            raise BusinessRuleError(
                "Permission denied for organization context.",
                code="PERMISSION_DENIED",
            )
        if self._user_session is not None:
            principal = self._user_session.principal
            if principal is not None and self._principal_rebuilder is not None:
                tenant_id = self.require_active_tenant_id(
                    operation_label="switch organization"
                )
                rebuilt = self._principal_rebuilder(tenant_id, organization.id)
                self._activate_rebuilt_context(
                    rebuilt,
                    switch_type="organization",
                )
            elif self._context_policy.mode is TenancyMode.SAAS:
                if principal is None:
                    raise BusinessRuleError(
                        "Authentication is required to switch organizations.",
                        code="AUTHENTICATION_REQUIRED",
                    )
                raise BusinessRuleError(
                    "Principal rebuilding is required for organization switching.",
                    code="PRINCIPAL_REBUILD_REQUIRED",
                )
            else:
                self._user_session.set_active_organization_id(organization.id)
        elif self._context_policy.mode is TenancyMode.SAAS:
            raise BusinessRuleError(
                "Authentication is required to switch organizations.",
                code="AUTHENTICATION_REQUIRED",
            )
        return organization

    def switch_to_tenant(self, tenant_id: str) -> Tenant:
        """Atomically switch tenant context.

        A failed authority rebuild leaves the previous principal and context
        untouched.
        """
        try:
            return self._switch_to_tenant(tenant_id)
        except DomainError as exc:
            self._record_context_switch_denial(
                switch_type="tenant",
                target_scope_id=tenant_id,
                error=exc,
            )
            raise

    def _switch_to_tenant(self, tenant_id: str) -> Tenant:
        if self._context_policy.mode is TenancyMode.SAAS and (
            self._user_session is None
            or self._user_session.principal is None
        ):
            raise BusinessRuleError(
                "Authentication is required to switch tenants.",
                code="AUTHENTICATION_REQUIRED",
            )
        tenant = self._require_available_tenant(tenant_id)
        if self._user_session is None:
            return tenant
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required to switch tenants.",
                code="AUTHENTICATION_REQUIRED",
            )
        is_platform_operator = "platform.admin" in getattr(
            principal,
            "permissions",
            frozenset(),
        )
        self.validate_principal_context(
            user_id=principal.user_id,
            is_platform_operator=is_platform_operator,
            tenant_id=tenant.id,
            organization_id=None,
        )
        organizations = self._organization_repo.list_for_tenant(
            tenant.id,
            active_only=True,
        )
        organization_id = organizations[0].id if len(organizations) == 1 else None
        if self._principal_rebuilder is None:
            raise BusinessRuleError(
                "Principal rebuilding is required for tenant switching.",
                code="PRINCIPAL_REBUILD_REQUIRED",
            )
        rebuilt = self._principal_rebuilder(tenant.id, organization_id)
        self._activate_rebuilt_context(rebuilt, switch_type="tenant")
        return tenant

    def _activate_rebuilt_context(
        self,
        principal: "UserSessionPrincipal",
        *,
        switch_type: str,
    ) -> None:
        committer = self._context_switch_committer
        if committer is not None:
            committer(principal, switch_type)
            return
        if self._context_policy.mode is TenancyMode.SAAS:
            raise BusinessRuleError(
                "Audited context switching is not configured.",
                code="CONTEXT_SWITCH_AUDIT_REQUIRED",
            )
        if self._user_session is not None:
            self._user_session.set_principal(principal)

    def _record_context_switch_denial(
        self,
        *,
        switch_type: str,
        target_scope_id: str,
        error: DomainError,
    ) -> None:
        record_authorization_denial(
            self._user_session,
            operation_label=f"switch {switch_type} context",
            reason_code=getattr(error, "code", error.__class__.__name__),
            target_scope_type=switch_type,
            target_scope_id=target_scope_id,
            operation=f"auth.context.{switch_type}.switch.denied",
        )

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

    def require_active_scope_ids(self, *, operation_label: str) -> ActiveScopeIds:
        """Fast path for repository-level SQL predicates: trust the session principal's
        already-validated `active_tenant_id`/`active_organization_id` instead of re-querying
        `tenants`/`organizations`
        """
        if self._user_session is None:
            ctx = self.require_organization_context(operation_label=operation_label)
            if ctx.organization_id is None:
                raise BusinessRuleError(
                    f"Active organization context is required for {operation_label}.",
                    code="ORGANIZATION_CONTEXT_REQUIRED",
                )
            return ActiveScopeIds(tenant_id=ctx.tenant_id, organization_id=ctx.organization_id)

        session_tenant_id = self._session_tenant_id()
        if not session_tenant_id:
            raise BusinessRuleError(
                f"Active tenant context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )

        organization_id = self._session_organization_id()
        if not organization_id:
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="ORGANIZATION_CONTEXT_REQUIRED",
            )
        return ActiveScopeIds(tenant_id=session_tenant_id, organization_id=organization_id)

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

    def _can_access(self, organization: Organization) -> bool:
        # Cross-tenant guard: org must belong to the currently active tenant.
        # Skipped only when no active tenant is set (single-tenant / bootstrap mode).
        active_tenant_id = self._session_tenant_id()
        if active_tenant_id:
            org_tenant_id = str(getattr(organization, "tenant_id", "") or "").strip()
            # H-5: deny access when org has no tenant_id while a tenant is active -
            # an unscoped org is ambiguous and must not be accessible in multi-tenant mode.
            if not org_tenant_id or org_tenant_id != active_tenant_id:
                return False

        if self._user_session is None:
            return True
        principal = self._user_session.principal
        if principal is None:
            return True
        if "admin" in getattr(principal, "role_names", frozenset()):
            return True
        if "tenant_admin" in getattr(principal, "role_names", frozenset()):
            return True
        if "platform.admin" in getattr(principal, "permissions", frozenset()):
            return True

        normalized_organization_id = str(organization.id or "").strip()
        if not normalized_organization_id:
            return False
        organization_scopes = dict((principal.scoped_access or {}).get("organization", {}))
        if organization_scopes:
            return normalized_organization_id in organization_scopes
        session_organization_id = str(
            getattr(self._user_session, "_active_organization_id", "") or ""
        ).strip()
        return bool(session_organization_id) and (
            session_organization_id == normalized_organization_id
        )


def require_tenant_context_service(
    tenant_context_service: TenantContextService | None,
    *,
    consumer_label: str,
) -> TenantContextService:
    if tenant_context_service is None:
        raise BusinessRuleError(
            f"{consumer_label} requires TenantContextService.",
            code="TENANT_CONTEXT_REQUIRED",
        )
    return tenant_context_service


__all__ = [
    "ActiveScopeIds",
    "TenantContext",
    "TenantContextService",
    "require_tenant_context_service",
]
