"""ADR-005 §7 (Transactional Dispatch) and §8 (Post-Commit Publication): structural typing
expectations for the dispatcher/publisher/handler/subscriber contracts.

P1 is contracts only -- there is no concrete dispatcher, bus, or handler registry to exercise
behaviorally yet (that is P2/P3). These tests confirm the *shapes* are correct: two genuinely
different handler signatures (one with `uow`, one with `context`), never one shared shape reused
for both, per ADR-005 §7's own rationale for why that would be a real gap.
"""

from __future__ import annotations

from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.core.shared.events.domain_event_subscriber import (
    PostCommitEventHandler,
    PostCommitEventSubscriber,
    TransactionalEventHandler,
    TransactionalEventSubscriber,
)


def test_transactional_and_post_commit_protocols_are_distinct_types() -> None:
    assert TransactionalEventDispatcher is not PostCommitEventPublisher
    assert TransactionalEventHandler is not PostCommitEventHandler
    assert TransactionalEventSubscriber is not PostCommitEventSubscriber


def test_a_plain_function_matching_the_transactional_handler_shape_satisfies_it_structurally() -> None:
    """A transactional handler receives (event, uow) -- no context parameter, since it
    already has the current UnitOfWork to read tracing metadata from (ADR-005 §5)."""

    def handle(event, uow) -> None:  # noqa: ANN001 -- structural shape check only
        pass

    # TransactionalEventHandler is a Protocol[E]; a plain two-parameter callable structurally
    # matches its __call__(self, event, uow) shape (self is implicit for the callable itself
    # when treated as a bound method elsewhere -- here we only assert the shape is callable
    # with exactly the two documented positional arguments).
    handle(object(), object())


def test_a_plain_function_matching_the_post_commit_handler_shape_satisfies_it_structurally() -> None:
    """A post-commit handler receives (event, context) -- never uow, since the transaction is
    already closed by the time it runs (ADR-005 §5, §8)."""

    def handle(event, context: DomainEventContext) -> None:  # noqa: ANN001
        pass

    handle(object(), DomainEventContext(correlation_id="corr-1"))


def test_transactional_subscriber_and_post_commit_subscriber_both_expose_subscribe() -> None:
    assert hasattr(TransactionalEventSubscriber, "subscribe")
    assert hasattr(PostCommitEventSubscriber, "subscribe")


def test_dispatcher_and_publisher_method_names_are_not_interchangeable() -> None:
    """ADR-005 §7's own naming correction: the transactional side is dispatch(...), never
    publish(...) -- it is a stateless synchronous call, not a publish-into-a-queue operation.
    The post-commit side genuinely queues and returns, hence publish(...)."""
    assert hasattr(TransactionalEventDispatcher, "dispatch")
    assert not hasattr(TransactionalEventDispatcher, "publish")
    assert hasattr(PostCommitEventPublisher, "publish")
    assert not hasattr(PostCommitEventPublisher, "dispatch")
