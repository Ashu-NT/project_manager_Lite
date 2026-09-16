from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
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

# SQLite permits only one writer at a time per database file.
#
# Each UnitOfWork owns an independent SQLAlchemy Session/connection. Concurrent
# write transactions within this process can therefore contend for SQLite's
# Serializing transactional dispatch and commit processing reduces
# in-process commit-time contention.
#
# This lock does not cover writes that may occur earlier through an explicit
# flush or SQLAlchemy autoflush, and it is process-local, so busy_timeout
# remains necessary for those cases and for writers in other processes.
#
# This lock is process-local; it does not serialize writers from other
# processes.
#
# Transactional event handlers must use the UnitOfWork supplied to them rather
# than opening an independent nested write UnitOfWork. A nested Session would
# still contend with the outer SQLite transaction at the database level.
#
# PostgreSQL supports concurrent writers and therefore bypasses this lock.
_SQLITE_WRITE_LOCK = threading.RLock()


@contextmanager
def _write_lock_for(session: Session) -> Generator[None, None, None]:
    try:
        is_sqlite = session.get_bind().dialect.name == "sqlite"
    except Exception:
        is_sqlite = False

    if is_sqlite:
        with _SQLITE_WRITE_LOCK:
            yield
    else:
        yield

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
        if self._closed:
            return None

        if exc_type is not None:
            self._rollback_and_close()
            return None

        logger.warning(
            "UnitOfWork exited its 'with' block without commit() ever being called; "
            "closing without committing."
        )
        self._rollback_and_close()
        return None
    # -- aggregate tracking -------------------------------------------------------------

    def register_touched(self, aggregate: RecordsDomainEvents) -> None:
        self._check_not_closed()
        self._tracked_aggregates[id(aggregate)] = aggregate

    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]:
        # Deliberately not closed-checked -- pending events may remain available for
        # inspection after a rollback
        return tuple(self._tracked_aggregates.values())

    def record_event(self, event: DomainEvent) -> None:
        """ orchestration escape hatch -- reserved for a fact with no natural
        aggregate owner. Never a substitute for an aggregate recording its own event."""
        self._check_not_closed()
        self._manually_recorded_events.append(event)

    # -- commit / rollback ---------------------------------------------------------------

    def commit(self) -> None:
        self._check_not_closed()

        collected_events: list[DomainEvent] = []

        try:
            with _write_lock_for(self._session):
                collected_events = self._drain_and_dispatch()
                self._session.commit()
                self._committed = True

        except Exception:
            try:
                self._session.rollback()
            except Exception:
                logger.exception(
                    "Rollback failed while handling UnitOfWork commit failure."
                )
            raise

        finally:
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
