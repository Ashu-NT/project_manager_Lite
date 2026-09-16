from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from typing import Self

from sqlalchemy.orm import Session

from src.core.shared.events.aggregate_events import RecordsDomainEvents
from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.core.shared.persistence.unit_of_work import (
    MaxDispatchRoundsExceededError,
    UnitOfWork,
    UnitOfWorkClosedError,
    UnitOfWorkFactory,
)

logger = logging.getLogger(__name__)

MAX_DISPATCH_ROUNDS = 20

# SQLite allows only one writer at a time for the whole database file, even in
# WAL mode. This app opens a fresh, independent Session/connection per
# UnitOfWork (see SqlAlchemyUnitOfWorkFactoryBase.create()), so two commands
# issued close together -- e.g. an Organization update and an Employee
# create, each recording its own activity entry in the same transaction --
# race for that single writer slot. `PRAGMA busy_timeout` (engine.py) makes
# the loser wait rather than fail outright, but only up to its window, and
# provides no ordering guarantee. Serializing writes in-process removes the
# race entirely: at most one UnitOfWork ever holds the write transaction at a
# time, so the busy_timeout becomes a true "should never happen" safety net
# instead of the primary defense. Reentrant so a domain-event handler that
# opens and commits another UnitOfWork from within this thread's own
# transactional dispatch doesn't deadlock on itself. Postgres (also
# supported -- see requirements-postgresql.txt) handles concurrent writers
# natively and must not pay this serialization cost.
_SQLITE_WRITE_LOCK = threading.RLock()


def _write_lock_for(session: Session) -> AbstractContextManager[None]:
    try:
        is_sqlite = session.get_bind().dialect.name == "sqlite"
    except Exception:
        is_sqlite = False
    return _SQLITE_WRITE_LOCK if is_sqlite else nullcontext()


class SqlAlchemyUnitOfWorkBase(UnitOfWork):
    def __init__(
        self,
        *,
        session: Session,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        context: DomainEventContext,
    ) -> None:
        self._session = session
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus
        self.context = context
        self._tracked_aggregates: dict[int, RecordsDomainEvents] = {}
        self._manually_recorded_events: list[DomainEvent] = []
        self._committed = False
        self._closed = False

    # -- context manager --------------------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            if not self._committed:
                self._rollback_and_close()
            return None  # never suppress the exception
        if not self._committed:

            logger.warning(
                "UnitOfWork exited its 'with' block without commit() ever being called; "
                "closing without committing."
            )
            self._rollback_and_close()
        # else: commit() already ran to completion and closed everything -- do nothing
        # further, per ADR-005 §9 ("on a clean exit it does nothing further").
        return None

    # -- aggregate tracking -------------------------------------------------------------

    def register_touched(self, aggregate: RecordsDomainEvents) -> None:
        self._check_not_closed()
        self._tracked_aggregates[id(aggregate)] = aggregate

    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]:
        # Deliberately not closed-checked -- pending events may remain available for
        # inspection after a rollback (ADR-005 §9's rollback-safety rule).
        return tuple(self._tracked_aggregates.values())

    def record_event(self, event: DomainEvent) -> None:
        """ADR-005 §6's orchestration escape hatch -- reserved for a fact with no natural
        aggregate owner. Never a substitute for an aggregate recording its own event."""
        self._check_not_closed()
        self._manually_recorded_events.append(event)

    # -- commit / rollback ---------------------------------------------------------------

    def commit(self) -> None:
        self._check_not_closed()
        with _write_lock_for(self._session):
            collected_events = self._drain_and_dispatch()
            self._session.commit()
            self._committed = True
        self._session.close()
        self._closed = True
        for aggregate in self._tracked_aggregates.values():
            aggregate.clear_domain_events()
        for event in collected_events:
            self._post_commit_bus.publish(event, self.context)

    def _rollback_and_close(self) -> None:
        try:
            self._session.rollback()
        finally:
            self._session.close()
            self._closed = True

    def _check_not_closed(self) -> None:
        if self._closed:
            raise UnitOfWorkClosedError(
                "This UnitOfWork has already been committed or rolled back; create a new "
                "UnitOfWork for further work."
            )

    # -- event collection / dispatch ------------------------------------------------------

    def _drain_and_dispatch(self) -> list[DomainEvent]:
        already_seen: set[int] = set()
        all_collected: list[DomainEvent] = []
        for _round in range(MAX_DISPATCH_ROUNDS):
            new_events = self._collect_new_events(already_seen)
            if not new_events:
                return all_collected
            for event in new_events:
                self._transactional_dispatcher.dispatch(event, self)  # FAIL_FAST -- propagates
            all_collected.extend(new_events)
        raise MaxDispatchRoundsExceededError(
            f"Transactional event dispatch did not quiesce within {MAX_DISPATCH_ROUNDS} "
            "rounds -- a real cycle in event-recording handlers is a bug, not a hang "
        )

    def _collect_new_events(self, already_seen: set[int]) -> list[DomainEvent]:
        new_events: list[DomainEvent] = []
        for aggregate in self.tracked_aggregates():
            for event in aggregate.domain_events():
                identity = id(event)
                if identity not in already_seen:
                    already_seen.add(identity)
                    new_events.append(event)
        for event in self._manually_recorded_events:
            identity = id(event)
            if identity not in already_seen:
                already_seen.add(identity)
                new_events.append(event)
        return new_events


class SqlAlchemyUnitOfWorkFactoryBase(UnitOfWorkFactory):
    """The module/capability-agnostic factory shape every module's own `SqlAlchemy<Module>UnitOfWorkFactory` """

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
    ) -> None:
        self._session_factory = session_factory
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus

    def create(self, *, context: DomainEventContext) -> SqlAlchemyUnitOfWorkBase:
        return SqlAlchemyUnitOfWorkBase(
            session=self._session_factory(),
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=context,
        )


__all__ = [
    "SqlAlchemyUnitOfWorkBase",
    "SqlAlchemyUnitOfWorkFactoryBase",
    "MAX_DISPATCH_ROUNDS",
]
