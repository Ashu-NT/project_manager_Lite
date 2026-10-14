"""Build Platform Approval with its fresh-session transaction factory."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.approval import (
    ApprovalCommandHandler,
    ApprovalParticipantRegistry,
    ApprovalQueryHandler,
)
from src.core.platform.application.approval.scope import ApprovalScope
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.uow.approval.approval_unit_of_work import (
    SqlAlchemyPlatformUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


@dataclass(frozen=True)
class ApprovalHandlers:
    commands: ApprovalCommandHandler
    queries: ApprovalQueryHandler
    participants: ApprovalParticipantRegistry


def build_approval_handlers(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> ApprovalHandlers:
    approval_uow_factory = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    participants = ApprovalParticipantRegistry()
    scope = ApprovalScope(tenant_context_service)
    return ApprovalHandlers(
        commands=ApprovalCommandHandler(
            uow_factory=approval_uow_factory,
            participants=participants,
            scope=scope,
            user_session=user_session,
            clock=SystemClock(),
        ),
        queries=ApprovalQueryHandler(
            approval_repo=repositories.approval_repo,
            scope=scope,
            user_session=user_session,
        ),
        participants=participants,
    )
