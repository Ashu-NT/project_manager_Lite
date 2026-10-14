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
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceCommandHandler,
    TenantRoleCommandHandler,
    TenantRoleQueryHandler,
)
from src.core.platform.application.security.authorization.roles.tenant_role_authorization import (
    TenantRoleAuthorization,
)
from src.core.platform.application.security.identity import (
    ApiKeyAuthenticationHandler,
    ServicePrincipalCommandHandler,
    ServicePrincipalQueryHandler,
)
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
from src.core.platform.domain.security.authorization.enforcement.sod import (
    SeparationOfDutiesPolicy,
)
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    AuthComposition,
)
from src.core.platform.infrastructure.composition.registrations.security.scope_resolvers import (
    ScopeResolvers,
)
from src.core.platform.infrastructure.persistence.uow.security.auth_unit_of_work import (
    SqlAlchemyAuthUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


@dataclass(frozen=True)
class SecurityAdministrationDependencies:
    service_principal_commands: ServicePrincipalCommandHandler
    service_principal_query: ServicePrincipalQueryHandler
    api_key_authentication: ApiKeyAuthenticationHandler
    access_service: AccessControlService
    tenant_role_commands: TenantRoleCommandHandler
    tenant_role_queries: TenantRoleQueryHandler


def build_security_administration_dependencies(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    auth: AuthComposition,
    role_governance_commands: RoleGovernanceCommandHandler,
    scope_resolvers: ScopeResolvers,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> SecurityAdministrationDependencies:
    service_principal_commands = ServicePrincipalCommandHandler(
        session=session,
        principal_repo=repositories.service_principal_repo,
        api_key_repo=repositories.api_key_credential_repo,
        user_repo=repositories.user_repo,
        audit_repo=repositories.audit_entry_repo,
        registration=auth.registration,
        principals=auth.principals,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    service_principal_query = ServicePrincipalQueryHandler(
        principal_repo=repositories.service_principal_repo,
        api_key_repo=repositories.api_key_credential_repo,
        user_repo=repositories.user_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    api_key_authentication = ApiKeyAuthenticationHandler(
        session=session,
        principal_repo=repositories.service_principal_repo,
        api_key_repo=repositories.api_key_credential_repo,
        user_repo=repositories.user_repo,
        tenant_repo=repositories.tenant_repo,
        organization_repo=repositories.organization_repo,
        membership_repo=repositories.user_tenant_repo,
        audit_repo=repositories.audit_entry_repo,
        principals=auth.principals,
    )
    access_service = AccessControlService(
        session=session,
        user_repo=repositories.user_repo,
        session_lifecycle=auth.session_lifecycle,
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
        role_governance_commands=role_governance_commands,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
    )
    tenant_role_authorization = TenantRoleAuthorization(
        role_binding_repo=repositories.role_binding_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        tenant_repo=repositories.tenant_repo,
        membership_repo=repositories.user_tenant_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        sod_policy=SeparationOfDutiesPolicy(),
    )
    tenant_role_queries = TenantRoleQueryHandler(
        role_repo=repositories.role_repo,
        authorization=tenant_role_authorization,
    )
    tenant_role_commands = TenantRoleCommandHandler(
        session=session,
        authorization=tenant_role_authorization,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        audit_repo=repositories.audit_entry_repo,
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        clock=SystemClock(),
        uow_factory=SqlAlchemyAuthUnitOfWorkFactory(),
    )
    return SecurityAdministrationDependencies(
        service_principal_commands=service_principal_commands,
        service_principal_query=service_principal_query,
        api_key_authentication=api_key_authentication,
        access_service=access_service,
        tenant_role_commands=tenant_role_commands,
        tenant_role_queries=tenant_role_queries,
    )
