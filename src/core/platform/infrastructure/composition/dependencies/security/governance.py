"""Build role governance and attach it to the shared Auth service."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceService,
)
from src.core.platform.application.tenant.tenancy import (
    TenancyMode,
    TenantContextService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.registrations.security.scope_resolvers import (
    ScopeResolvers,
)
from src.core.platform.infrastructure.persistence.uow.role_governance_unit_of_work import (
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


def build_role_governance_service(
    *,
    session: Session,
    auth_service: AuthService,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    security_configuration: RuntimeSecurityConfiguration,
    scope_resolvers: ScopeResolvers,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> RoleGovernanceService:
    uow_factory = SqlAlchemyRoleGovernanceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
    service = RoleGovernanceService(
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
    auth_service.set_role_governance_service(service)
    return service
