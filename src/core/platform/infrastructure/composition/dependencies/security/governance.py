"""Build role governance and the role-assignment handler that uses it."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceCommandHandler,
)
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.application.tenant.tenancy import (
    TenancyMode,
    TenantContextService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    AuthComposition,
)
from src.core.platform.infrastructure.composition.registrations.security.scope_resolvers import (
    ScopeResolvers,
)
from src.core.platform.infrastructure.persistence.uow.security.role_governance_unit_of_work import (
    SqlAlchemyRoleGovernanceUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.platform.security_config import RuntimeSecurityConfiguration
from src.infra.time.system_clock import SystemClock


def build_role_governance_commands(
    *,
    session: Session,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    security_configuration: RuntimeSecurityConfiguration,
    scope_resolvers: ScopeResolvers,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> RoleGovernanceCommandHandler:
    uow_factory = SqlAlchemyRoleGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
    return RoleGovernanceCommandHandler(
        uow_factory=uow_factory,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        clock=SystemClock(),
        scope_exists_resolvers=scope_resolvers.governance,
        organization_owner_resolvers=scope_resolvers.organization_owner,
        allow_platform_customer_context=(
            security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT
        ),
    )


def build_role_assignment_handler(
    *,
    repositories: PlatformRepositories,
    auth: AuthComposition,
    role_governance_commands: RoleGovernanceCommandHandler,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
) -> RoleAssignmentHandler:
    return RoleAssignmentHandler(
        auth_queries=auth.queries,
        role_binding_repo=repositories.role_binding_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        user_tenant_repo=repositories.user_tenant_repo,
        target_users=auth.target_users,
        lifecycle=auth.session_lifecycle,
        role_governance_commands=role_governance_commands,
    )
