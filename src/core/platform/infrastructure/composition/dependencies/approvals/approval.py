"""Build Platform Approval with its fresh-session transaction factory."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.persistence.uow.approval_unit_of_work import (
    SqlAlchemyPlatformUnitOfWorkFactory,
)
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


def build_approval_service(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    enterprise_audit_service: EnterpriseAuditService,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> ApprovalService:
    approval_uow_factory = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    return ApprovalService(
        session=session,
        approval_repo=repositories.approval_repo,
        uow_factory=approval_uow_factory,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        clock=SystemClock(),
    )
