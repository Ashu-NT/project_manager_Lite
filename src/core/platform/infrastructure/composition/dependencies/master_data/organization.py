"""Build the organization service with a fresh-session UoW."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationQueryHandler,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.org.default_calendar_writer import (
    SqlAlchemyOrganizationDefaultCalendarWriter,
)
from src.core.platform.infrastructure.persistence.uow.master_data.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


@dataclass(frozen=True)
class OrganizationComposition:
    commands: OrganizationCommandHandler
    lifecycle: OrganizationLifecycleCommandHandler
    query: OrganizationQueryHandler


def build_organization_handlers(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    overview_rollup_reader: SqlAlchemyPlatformOverviewRollupReader,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> OrganizationComposition:
    organization_uow_factory = SqlAlchemyOrganizationUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    clock = SystemClock()
    return OrganizationComposition(
        commands=OrganizationCommandHandler(
            organization_repo=repositories.organization_repo,
            uow_factory=organization_uow_factory,
            default_calendar_writer=SqlAlchemyOrganizationDefaultCalendarWriter(),
            clock=clock,
            user_session=user_session,
        ),
        lifecycle=OrganizationLifecycleCommandHandler(
            uow_factory=organization_uow_factory,
            clock=clock,
            user_session=user_session,
        ),
        query=OrganizationQueryHandler(
            session=session,
            organization_repo=repositories.organization_repo,
            user_session=user_session,
            enterprise_audit_service=enterprise_audit_service,
            overview_rollup_reader=overview_rollup_reader,
            employee_headcount_reader=SqlAlchemyEmployeeHeadcountReader(session),
        ),
    )


__all__ = ["OrganizationComposition", "build_organization_handlers"]
