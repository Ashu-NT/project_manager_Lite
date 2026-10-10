"""Build Platform document, party, site, and department services."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.department.department_service import (
    DepartmentService,
)
from src.core.platform.application.master_data.documents import (
    DocumentIntegrationService,
    DocumentService,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.core.platform.infrastructure.persistence.uow.department_unit_of_work import (
    SqlAlchemyDepartmentUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.party_unit_of_work import (
    SqlAlchemyPartyUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.site_unit_of_work import (
    SqlAlchemySiteUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


@dataclass(frozen=True)
class MasterDataDependencies:
    document_service: DocumentService
    document_integration_service: DocumentIntegrationService
    party_service: PartyService
    site_service: SiteService
    department_service: DepartmentService


def build_master_data_dependencies(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    overview_rollup_reader: SqlAlchemyPlatformOverviewRollupReader,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> MasterDataDependencies:
    document_uow_factory = SqlAlchemyDocumentUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    document_service = DocumentService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=document_uow_factory,
        clock=SystemClock(),
    )
    document_integration_service = DocumentIntegrationService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        uow_factory=document_uow_factory,
        clock=SystemClock(),
    )
    party_uow_factory = SqlAlchemyPartyUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    party_service = PartyService(
        session=session,
        party_repo=repositories.party_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=party_uow_factory,
        clock=SystemClock(),
    )
    site_uow_factory = SqlAlchemySiteUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    site_service = SiteService(
        session=session,
        site_repo=repositories.site_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=site_uow_factory,
        clock=SystemClock(),
    )
    department_uow_factory = SqlAlchemyDepartmentUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    department_service = DepartmentService(
        session=session,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        employee_repo=repositories.employee_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=department_uow_factory,
        clock=SystemClock(),
    )
    return MasterDataDependencies(
        document_service=document_service,
        document_integration_service=document_integration_service,
        party_service=party_service,
        site_service=site_service,
        department_service=department_service,
    )
