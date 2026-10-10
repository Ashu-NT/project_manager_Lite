"""Build Platform service identity, scoped access, and role administration."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.access import (
    AccessControlService,
    ScopedRolePolicy,
    ScopedRolePolicyRegistry,
)
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceService,
    TenantRoleAdministrationService,
)
from src.core.platform.application.security.identity import ServicePrincipalService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.master_data.org.access_policy import (
    ORGANIZATION_SCOPE_ROLE_CHOICES,
    normalize_organization_scope_role,
    resolve_organization_scope_permissions,
)
from src.core.platform.domain.master_data.site.access_policy import (
    SITE_SCOPE_ROLE_CHOICES,
    normalize_site_scope_role,
    resolve_site_scope_permissions,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.composition.registrations.security.scope_resolvers import (
    ScopeResolvers,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)


@dataclass(frozen=True)
class SecurityAdministrationDependencies:
    service_principal_service: ServicePrincipalService
    access_service: AccessControlService
    tenant_role_administration_service: TenantRoleAdministrationService


def build_security_administration_dependencies(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    auth_service: AuthService,
    role_governance_service: RoleGovernanceService,
    scope_resolvers: ScopeResolvers,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> SecurityAdministrationDependencies:
    service_principal_service = ServicePrincipalService(
        session=session,
        principal_repo=repositories.service_principal_repo,
        api_key_repo=repositories.api_key_credential_repo,
        user_repo=repositories.user_repo,
        tenant_repo=repositories.tenant_repo,
        organization_repo=repositories.organization_repo,
        membership_repo=repositories.user_tenant_repo,
        audit_repo=repositories.audit_entry_repo,
        auth_service=auth_service,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    access_service = AccessControlService(
        session=session,
        user_repo=repositories.user_repo,
        auth_service=auth_service,
        policy_registry=ScopedRolePolicyRegistry(
            (
                ScopedRolePolicy(
                    scope_type="site",
                    role_choices=SITE_SCOPE_ROLE_CHOICES,
                    normalize_role=normalize_site_scope_role,
                    resolve_permissions=resolve_site_scope_permissions,
                ),
                ScopedRolePolicy(
                    scope_type="organization",
                    role_choices=ORGANIZATION_SCOPE_ROLE_CHOICES,
                    normalize_role=normalize_organization_scope_role,
                    resolve_permissions=resolve_organization_scope_permissions,
                ),
            )
        ),
        scope_exists_resolvers=scope_resolvers.access,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        user_tenant_repo=repositories.user_tenant_repo,
        tenant_context_service=tenant_context_service,
        role_governance_service=role_governance_service,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
    )
    tenant_role_administration_service = TenantRoleAdministrationService(
        session=session,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        tenant_repo=repositories.tenant_repo,
        membership_repo=repositories.user_tenant_repo,
        audit_repo=repositories.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
    return SecurityAdministrationDependencies(
        service_principal_service=service_principal_service,
        access_service=access_service,
        tenant_role_administration_service=tenant_role_administration_service,
    )
