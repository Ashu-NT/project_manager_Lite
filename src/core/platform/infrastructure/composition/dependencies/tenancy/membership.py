"""Build tenant membership mutation on a fresh-session UoW."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.tenant.tenancy import (
    TenantContextService,
    TenantMembershipService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.registrations.security.scope_resolvers import (
    ScopeResolvers,
)
from src.core.platform.infrastructure.persistence.uow.tenant_membership_unit_of_work import (
    SqlAlchemyTenantMembershipUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


def build_tenant_membership_service(
    *,
    session: Session,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    scope_resolvers: ScopeResolvers,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> TenantMembershipService:
    uow_factory = SqlAlchemyTenantMembershipUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
    )
    return TenantMembershipService(
        uow_factory=uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        organization_owner_resolvers=scope_resolvers.organization_owner,
    )
