"""Build the organization service with a fresh-session UoW."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.core.platform.infrastructure.persistence.uow.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWorkFactory,
)
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


def build_organization_service(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    overview_rollup_reader: SqlAlchemyPlatformOverviewRollupReader,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> OrganizationService:
    organization_uow_factory = SqlAlchemyOrganizationUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    return OrganizationService(
        session=session,
        organization_repo=repositories.organization_repo,
        uow_factory=organization_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        employee_headcount_reader=SqlAlchemyEmployeeHeadcountReader(session),
    )
