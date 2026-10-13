from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase


class SqlAlchemyAuthUnitOfWorkFactory:
    def create(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher | None,
        post_commit_bus: PostCommitEventPublisher | None,
    ) -> SqlAlchemyUnitOfWorkBase:
        if transactional_dispatcher is None or post_commit_bus is None:
            raise RuntimeError(
                "Auth service is missing its transactional dispatcher / post-commit bus -- "
                "durable Auth/Security mutations require both to be wired; there is no "
                "degraded fallback."
            )
        return SqlAlchemyUnitOfWorkBase(
            session=session,
            transactional_dispatcher=transactional_dispatcher,
            post_commit_bus=post_commit_bus,
            context=DomainEventContext(correlation_id=generate_id()),
        )
