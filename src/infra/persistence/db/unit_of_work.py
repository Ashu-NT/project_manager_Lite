"""ADR-005 §9/§10/§6.1: `SqlAlchemyUnitOfWorkBase` -- the concrete, module/capability-agnostic
foundation every module's own `SqlAlchemy<Module>UnitOfWork` subclass (P4+) builds on.

REPLACES this file's previous content, `session_scope()` -- confirmed twice by the Platform
audit to have zero callers anywhere in `src/`, so reclaiming the enterprise-standard name for
the real Unit of Work costs no import-site migration (ADR-005 §6.1). Nothing is deleted
outright: `session_scope()`'s try/commit/except-rollback/finally-close shape is folded in below
as the private lifecycle `commit()`/`_rollback_and_close()` use internally.

Owns: session lifecycle (one fresh `Session` per instance -- never the existing process-lifetime
`Session` `RepositoryBundle` still uses), identity-map aggregate tracking (keyed by `id()`,
never a `set` -- aggregates are not guaranteed hashable, and identity, not equality, is the
correct dedup semantics per ADR-005 §10), the collect-dispatch-recollect draining loop with a
`MAX_DISPATCH_ROUNDS` cycle guard, and post-commit publication. Declares no repository
accessors and exposes no public `session` attribute -- a future capability/module-specific
subclass (P4+) adds typed repository accessors of its own; this base class has no abstract
methods and needs no subclass to be constructed, tested, or used on its own.

Deliberately does NOT wire any Platform capability, ApprovalService, NotificationService, or
business module onto this -- that is P4+ (Platform transaction convergence) and later module
migration phases. Zero real consumers reference this file yet.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

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

# ADR-005 does not mandate a specific numeric limit -- this is an implementation-chosen safety
# net, not an architectural decision. A real business dispatch chain is expected to quiesce in
# a handful of rounds; this exists purely to fail loudly on a genuine cycle rather than hang.
MAX_DISPATCH_ROUNDS = 20


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

    def __enter__(self) -> "SqlAlchemyUnitOfWorkBase":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            if not self._committed:
                self._rollback_and_close()
            # else: the transaction already committed successfully before this later,
            # unrelated exception occurred -- there is nothing left to roll back, and
            # commit() already closed the session.
            return None  # never suppress the exception
        if not self._committed:
            # A caller exited the `with` block cleanly without ever calling commit().
            # ADR-005 §9 states commit() is always explicit and never implied by a clean
            # exit -- this specific case (no exception, but commit() never reached) is not
            # itself addressed by that text. Resolved here as a documented safety net
            # (close without committing) rather than silently leaking an open Session --
            # see the P3 implementation report for this call.
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
            # Deliberately do NOT clear self._tracked_aggregates here. ADR-005 §9's
            # rollback-safety rule is "discarded... never reused," not "erased from
            # memory" -- pending events may remain available via tracked_aggregates()
            # for post-mortem inspection (which is exactly why that method is not
            # closed-checked, unlike register_touched/record_event/commit). "Discarded"
            # is enforced structurally by _check_not_closed() refusing any further
            # mutation on this now-closed instance, never by physically clearing state a
            # caller may still legitimately want to read.

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
            "(ADR-005 §10)."
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
    """The module/capability-agnostic factory shape every module's own
    `SqlAlchemy<Module>UnitOfWorkFactory` (P4+) follows -- closes over a session *factory*
    (e.g. `SessionLocal`), never an already-created `Session`, so every `create()` call opens
    a genuinely new `Session` (ADR-005 §6.1's round-four correction). Usable directly wherever
    no module-specific repository accessors are needed."""

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
