"""ADR-005 §7: `InProcessTransactionalEventDispatcher`.

P2 is transaction-neutral -- `uow` is an opaque object these tests pass through and assert is
forwarded unchanged; no real UnitOfWork exists yet (P3), and this dispatcher never needs one to
be a real type, since it never inspects `uow` at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)


@dataclass(frozen=True, slots=True)
class _FakeTaskCompleted:
    occurred_at: datetime = datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _FakeOtherEvent:
    occurred_at: datetime = datetime.now(timezone.utc)


@pytest.fixture()
def dispatcher() -> InProcessTransactionalEventDispatcher:
    return InProcessTransactionalEventDispatcher()


def test_registered_handler_is_called_with_event_and_uow_unchanged(dispatcher) -> None:
    received: list[tuple[object, object]] = []

    def handler(event, uow) -> None:
        received.append((event, uow))

    dispatcher.subscribe(_FakeTaskCompleted, handler)

    event = _FakeTaskCompleted()
    fake_uow = object()
    dispatcher.dispatch(event, fake_uow)

    assert received == [(event, fake_uow)]


def test_multiple_handlers_for_the_same_event_type_all_execute_in_registration_order(dispatcher) -> None:
    order: list[str] = []
    dispatcher.subscribe(_FakeTaskCompleted, lambda e, u: order.append("first"))
    dispatcher.subscribe(_FakeTaskCompleted, lambda e, u: order.append("second"))
    dispatcher.subscribe(_FakeTaskCompleted, lambda e, u: order.append("third"))

    dispatcher.dispatch(_FakeTaskCompleted(), object())

    assert order == ["first", "second", "third"]


def test_dispatching_an_event_with_no_registered_handlers_is_a_no_op(dispatcher) -> None:
    # Must not raise -- an event type nobody subscribed to simply has zero handlers to call.
    dispatcher.dispatch(_FakeOtherEvent(), object())


def test_handler_registered_for_a_different_event_type_is_never_called(dispatcher) -> None:
    calls: list[str] = []
    dispatcher.subscribe(_FakeOtherEvent, lambda e, u: calls.append("wrong-type"))

    dispatcher.dispatch(_FakeTaskCompleted(), object())

    assert calls == [], "handler dispatch is by exact event type only (ADR-005 Test Impact)"


def test_fail_fast_propagates_and_stops_remaining_handlers(dispatcher) -> None:
    calls: list[str] = []

    def first(event, uow) -> None:
        calls.append("first")

    def second_raises(event, uow) -> None:
        calls.append("second")
        raise ValueError("business rule violated")

    def third_never_runs(event, uow) -> None:
        calls.append("third")

    dispatcher.subscribe(_FakeTaskCompleted, first)
    dispatcher.subscribe(_FakeTaskCompleted, second_raises)
    dispatcher.subscribe(_FakeTaskCompleted, third_never_runs)

    with pytest.raises(ValueError, match="business rule violated"):
        dispatcher.dispatch(_FakeTaskCompleted(), object())

    assert calls == ["first", "second"], "the third handler must not run once the second raised"


def test_dispatcher_does_not_catch_and_continue_on_failure(dispatcher) -> None:
    """FAIL_FAST is structural: the dispatcher itself must never decide to isolate a
    transactional handler's failure -- that would silently break the atomicity guarantee a
    future UnitOfWork relies on (ADR-005 §7/§16)."""

    def boom(event, uow) -> None:
        raise RuntimeError("must propagate")

    dispatcher.subscribe(_FakeTaskCompleted, boom)

    with pytest.raises(RuntimeError):
        dispatcher.dispatch(_FakeTaskCompleted(), object())


def test_dispatcher_is_stateless_across_dispatch_calls(dispatcher) -> None:
    """No pending events, queued handlers, or failed-event state leaks between dispatch()
    calls -- confirmed by dispatching successfully, for a different event type, immediately
    after a prior call raised for the first event type."""
    calls: list[str] = []

    def boom(event, uow) -> None:
        raise ValueError("first call fails")

    def ok(event, uow) -> None:
        calls.append("ok")

    dispatcher.subscribe(_FakeTaskCompleted, boom)
    dispatcher.subscribe(_FakeOtherEvent, ok)

    with pytest.raises(ValueError):
        dispatcher.dispatch(_FakeTaskCompleted(), object())

    # A completely unrelated dispatch() call right after a failure must behave normally --
    # nothing about the prior failure is retained anywhere in the dispatcher.
    dispatcher.dispatch(_FakeOtherEvent(), object())
    assert calls == ["ok"]

    # And dispatching the original failing event type again still fails the same way --
    # the dispatcher did not silently unregister or mutate anything on failure.
    with pytest.raises(ValueError):
        dispatcher.dispatch(_FakeTaskCompleted(), object())


def test_two_concurrent_dispatch_calls_with_different_uows_never_cross_contaminate() -> None:
    """Confirms no cross-transaction bug is possible by construction: the dispatcher holds no
    per-call state beyond a lock-protected handler-registry snapshot, so concurrent dispatch()
    calls from different threads, each with its own uow, cannot leak one call's uow into
    another's handler invocation (ADR-005 §7/§9, the exact bug round four of the ADR's design
    history fixed by making this side stateless)."""
    import threading

    dispatcher = InProcessTransactionalEventDispatcher()
    observed: list[tuple[object, object]] = []
    lock = threading.Lock()

    def handler(event, uow) -> None:
        with lock:
            observed.append((event, uow))

    dispatcher.subscribe(_FakeTaskCompleted, handler)

    uow_a = object()
    uow_b = object()
    event_a = _FakeTaskCompleted()
    event_b = _FakeTaskCompleted()

    thread_a = threading.Thread(target=lambda: dispatcher.dispatch(event_a, uow_a))
    thread_b = threading.Thread(target=lambda: dispatcher.dispatch(event_b, uow_b))

    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=5)
    thread_b.join(timeout=5)

    assert len(observed) == 2
    for observed_event, observed_uow in observed:
        if observed_event is event_a:
            assert observed_uow is uow_a
        else:
            assert observed_event is event_b
            assert observed_uow is uow_b


def test_subscription_dispose_is_idempotent(dispatcher) -> None:
    calls: list[str] = []
    subscription = dispatcher.subscribe(_FakeTaskCompleted, lambda e, u: calls.append("x"))

    subscription.dispose()
    subscription.dispose()  # must not raise

    dispatcher.dispatch(_FakeTaskCompleted(), object())
    assert calls == []


def test_disposing_one_subscription_does_not_affect_an_independent_identical_subscription(
    dispatcher,
) -> None:
    """Duplicate registration is independent, never deduplicated (implementation default,
    matching the ADR's own list-based registry pattern -- see module docstring)."""
    calls: list[str] = []

    def handler(event, uow) -> None:
        calls.append("hit")

    first_subscription = dispatcher.subscribe(_FakeTaskCompleted, handler)
    dispatcher.subscribe(_FakeTaskCompleted, handler)  # same handler, independent registration

    first_subscription.dispose()

    dispatcher.dispatch(_FakeTaskCompleted(), object())
    assert calls == ["hit"], "one of the two identical registrations must still be live"
