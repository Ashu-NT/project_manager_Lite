"""ADR-005 §7 (Transactional Dispatch) and §8 (Post-Commit Publication) -- contracts only.

No concrete implementation, no handler registry, no recursion/cycle logic here -- those are
P2 (`src/infra/events/in_process_transactional_event_dispatcher.py`,
`in_process_post_commit_event_bus.py`) and P3 (the UnitOfWork's own draining loop) concerns.

Two genuinely different contracts, not one shared shape reused for both: a transactional
handler needs the current `UnitOfWork` to safely touch another aggregate in the same
transaction (FAIL_FAST -- a failure rolls back everything); a post-commit handler must not have
it, since the transaction is already closed by the time it runs (ISOLATE_AND_CONTINUE -- one
handler's failure never blocks another, or rolls back the already-committed business action).
"""

from __future__ import annotations

from typing import Protocol

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext

# `UnitOfWork` is defined in P3 (src/core/shared/persistence/unit_of_work.py), which does not
# exist yet -- P1 must not depend on it. Referenced below as a bare forward reference only:
# `from __future__ import annotations` makes every annotation in this module a lazy string, so
# this name is never resolved (no NameError) unless something calls typing.get_type_hints() on
# these Protocols, which nothing in P1 does. No import of a nonexistent module is needed.


class TransactionalEventDispatcher(Protocol):
    def dispatch(self, event: DomainEvent, uow: UnitOfWork) -> None: ...


class PostCommitEventPublisher(Protocol):
    def publish(self, event: DomainEvent, context: DomainEventContext) -> None: ...


__all__ = ["TransactionalEventDispatcher", "PostCommitEventPublisher"]
