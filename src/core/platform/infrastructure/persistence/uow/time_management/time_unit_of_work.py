from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase


class SqlAlchemyTimeUnitOfWorkFactory:
    def create(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
    ) -> SqlAlchemyUnitOfWorkBase:
        return SqlAlchemyUnitOfWorkBase(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=context,
        )
