from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.uow.collaboration.collaboration_unit_of_work import (
    CollaborationUnitOfWork,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
    SqlAlchemyTaskCommentRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.postgresql_rls import configure_session_rls_context
from src.infra.persistence.db.unit_of_work import (
    SqlAlchemyUnitOfWorkBase,
    SqlAlchemyUnitOfWorkFactoryBase,
)


class SqlAlchemyCollaborationUnitOfWork(SqlAlchemyUnitOfWorkBase, CollaborationUnitOfWork):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
        self.comments = SqlAlchemyTaskCommentRepository(session)
        if hasattr(self.comments, "_tenant_context_service"):
            self.comments._tenant_context_service = tenant_context_service

        audit_repo = SqlAlchemyAuditRepository(session)
        audit_repo._tenant_context_service = tenant_context_service
        self._enterprise_audit_service = EnterpriseAuditService(
            session=session,
            audit_repo=audit_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )


class SqlAlchemyCollaborationUnitOfWorkFactory(SqlAlchemyUnitOfWorkFactoryBase):
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service,
        user_session,
    ) -> None:
        super().__init__(
            session_factory=session_factory,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
        )
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    def create(self, *, context: DomainEventContext) -> SqlAlchemyCollaborationUnitOfWork:
        session = self._session_factory()
        configure_session_rls_context(session, user_session=self._user_session)
        return SqlAlchemyCollaborationUnitOfWork(
            session=session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
            tenant_context_service=self._tenant_context_service,
            user_session=self._user_session,
        )


__all__ = ["SqlAlchemyCollaborationUnitOfWork", "SqlAlchemyCollaborationUnitOfWorkFactory"]
