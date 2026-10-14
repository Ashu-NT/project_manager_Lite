"""Build the Platform document, party, site and department handlers."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.department import (
    DepartmentCommandHandler,
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.documents import (
    DocumentAttachmentCommandHandler,
    DocumentAttachmentQueryHandler,
    DocumentCommandHandler,
    DocumentQueryHandler,
    DocumentStructureCommandHandler,
    PermissionDocumentAccessPolicy,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.core.platform.infrastructure.persistence.uow.master_data.department_unit_of_work import (
    SqlAlchemyDepartmentUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.master_data.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.master_data.party_unit_of_work import (
    SqlAlchemyPartyUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.master_data.site_unit_of_work import (
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
    document_access_policy: PermissionDocumentAccessPolicy
    document_commands: DocumentCommandHandler
    document_structure_commands: DocumentStructureCommandHandler
    document_query: DocumentQueryHandler
    document_attachment_commands: DocumentAttachmentCommandHandler
    document_attachment_query: DocumentAttachmentQueryHandler
    party_commands: PartyCommandHandler
    party_query: PartyQueryHandler
    site_commands: SiteCommandHandler
    site_query: SiteQueryHandler
    department_commands: DepartmentCommandHandler
    department_query: DepartmentQueryHandler


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
    # One policy per runtime: modules register RESTRICTED-document rules on it.
    document_access_policy = PermissionDocumentAccessPolicy(user_session=user_session)
    document_commands = DocumentCommandHandler(
        uow_factory=document_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        access_policy=document_access_policy,
    )
    document_structure_commands = DocumentStructureCommandHandler(
        uow_factory=document_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    document_query = DocumentQueryHandler(
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        access_policy=document_access_policy,
    )
    document_attachment_commands = DocumentAttachmentCommandHandler(
        structure_repo=repositories.document_structure_repo,
        uow_factory=document_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        access_policy=document_access_policy,
    )
    document_attachment_query = DocumentAttachmentQueryHandler(
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        access_policy=document_access_policy,
    )
    party_uow_factory = SqlAlchemyPartyUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    party_commands = PartyCommandHandler(
        uow_factory=party_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    party_query = PartyQueryHandler(
        party_repo=repositories.party_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
    )
    site_uow_factory = SqlAlchemySiteUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    site_commands = SiteCommandHandler(
        uow_factory=site_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    site_query = SiteQueryHandler(
        site_repo=repositories.site_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
    )
    department_uow_factory = SqlAlchemyDepartmentUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    department_commands = DepartmentCommandHandler(
        uow_factory=department_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    department_query = DepartmentQueryHandler(
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
    )
    return MasterDataDependencies(
        document_access_policy=document_access_policy,
        document_commands=document_commands,
        document_structure_commands=document_structure_commands,
        document_query=document_query,
        document_attachment_commands=document_attachment_commands,
        document_attachment_query=document_attachment_query,
        party_commands=party_commands,
        party_query=party_query,
        site_commands=site_commands,
        site_query=site_query,
        department_commands=department_commands,
        department_query=department_query,
    )
