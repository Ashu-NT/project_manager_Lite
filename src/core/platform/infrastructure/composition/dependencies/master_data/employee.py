"""Assemble the employee handlers on the shared Platform event buses."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.master_data.documents import (
    DocumentCommandHandler,
    DocumentQueryHandler,
)
from src.core.platform.application.master_data.employee import (
    EmployeeCommandHandler,
    EmployeeDocumentCommandHandler,
    EmployeeQueryHandler,
)
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.core.platform.infrastructure.persistence.uow.master_data.employee_unit_of_work import (
    SqlAlchemyEmployeeUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


@dataclass(frozen=True)
class EmployeeComposition:
    commands: EmployeeCommandHandler
    documents: EmployeeDocumentCommandHandler
    query: EmployeeQueryHandler


def build_employee_handlers(
    *,
    session: Session,
    repositories: PlatformRepositories,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    document_commands: DocumentCommandHandler,
    document_query: DocumentQueryHandler,
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
) -> EmployeeComposition:
    employee_uow_factory = SqlAlchemyEmployeeUnitOfWorkFactory(
        session_factory=sessionmaker(bind=session.bind, future=True),
        transactional_dispatcher=transactional_dispatcher,
        post_commit_bus=post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    return EmployeeComposition(
        commands=EmployeeCommandHandler(
            uow_factory=employee_uow_factory,
            clock=SystemClock(),
            organization_repo=repositories.organization_repo,
            user_repo=repositories.user_repo,
            user_tenant_repo=repositories.user_tenant_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        ),
        documents=EmployeeDocumentCommandHandler(
            employee_repo=repositories.employee_repo,
            document_commands=document_commands,
            document_query=document_query,
            uow_factory=employee_uow_factory,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        ),
        query=EmployeeQueryHandler(
            employee_repo=repositories.employee_repo,
            organization_repo=repositories.organization_repo,
            headcount_reader=SqlAlchemyEmployeeHeadcountReader(session),
            document_query=document_query,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        ),
    )


__all__ = ["EmployeeComposition", "build_employee_handlers"]
