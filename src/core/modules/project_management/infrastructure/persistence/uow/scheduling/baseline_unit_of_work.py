from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase


class SqlAlchemyBaselineUnitOfWork(SqlAlchemyUnitOfWorkBase):
    def commit(self) -> None:
        self._check_not_closed()
        collected_events = self._drain_and_dispatch()
        self._session.commit()
        self._committed = True
        self._closed = True
        for aggregate in self._tracked_aggregates.values():
            aggregate.clear_domain_events()
        for event in collected_events:
            self._post_commit_bus.publish(event, self.context)

    def _rollback_and_close(self) -> None:
        self._session.rollback()
        self._closed = True


class SqlAlchemyBaselineUnitOfWorkFactory:
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
    ) -> None:
        self._session = session
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus

    def create(self) -> SqlAlchemyBaselineUnitOfWork:
        return SqlAlchemyBaselineUnitOfWork(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=DomainEventContext(correlation_id=generate_id()),
        )


__all__ = ["SqlAlchemyBaselineUnitOfWork", "SqlAlchemyBaselineUnitOfWorkFactory"]
