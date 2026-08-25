"""ADR-005 §8: `InProcessPostCommitEventBus`.

Covers: registered-handler execution, ISOLATE_AND_CONTINUE, re-entrant publication with
explicit breadth-first ordering (a deliberate design change from the legacy Signal's accidental
depth-first-under-recursion, pinned down in P0's characterization test), the empty-queue/
`_dispatching`-flip race fix (an adversarial, deliberately-interleaved test), lock-held
handler-registry snapshot semantics under concurrent subscribe/dispose, queue cleanup after a
top-level publish, and disposal.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus


@dataclass(frozen=True, slots=True)
class _EventA:
    occurred_at: datetime = datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _EventB:
    occurred_at: datetime = datetime.now(timezone.utc)


@pytest.fixture()
def bus() -> InProcessPostCommitEventBus:
    return InProcessPostCommitEventBus()


@pytest.fixture()
def context() -> DomainEventContext:
    return DomainEventContext(correlation_id="corr-1")


def test_registered_handlers_execute_with_event_and_context(bus, context) -> None:
    received: list[tuple[object, object]] = []
    bus.subscribe(_EventA, lambda e, c: received.append((e, c)))

    event = _EventA()
    bus.publish(event, context)

    assert received == [(event, context)]


def test_unregistered_event_type_is_a_no_op(bus, context) -> None:
    bus.publish(_EventB(), context)  # must not raise -- zero handlers for this type


def test_multiple_handlers_all_execute(bus, context) -> None:
    order: list[str] = []
    bus.subscribe(_EventA, lambda e, c: order.append("first"))
    bus.subscribe(_EventA, lambda e, c: order.append("second"))

    bus.publish(_EventA(), context)

    assert order == ["first", "second"]


def test_isolate_and_continue_one_failure_does_not_block_sibling_handlers(bus, context, caplog) -> None:
    calls: list[str] = []

    def fails(event, ctx) -> None:
        calls.append("fails")
        raise ValueError("handler bug")

    def succeeds(event, ctx) -> None:
        calls.append("succeeds")

    bus.subscribe(_EventA, fails)
    bus.subscribe(_EventA, succeeds)

    with caplog.at_level(logging.ERROR):
        bus.publish(_EventA(), context)  # must not raise

    assert calls == ["fails", "succeeds"]
    assert any("Post-commit handler failed" in record.message for record in caplog.records), (
        "a failure must be recorded/logged, not operationally invisible"
    )


def test_isolate_and_continue_does_not_propagate_the_exception(bus, context) -> None:
    def fails(event, ctx) -> None:
        raise RuntimeError("must be isolated")

    bus.subscribe(_EventA, fails)

    bus.publish(_EventA(), context)  # no pytest.raises -- must complete normally


def test_multiple_failures_are_all_isolated_and_all_logged(bus, context, caplog) -> None:
    calls: list[str] = []

    def fail_one(event, ctx) -> None:
        calls.append("one")
        raise ValueError("first failure")

    def fail_two(event, ctx) -> None:
        calls.append("two")
        raise ValueError("second failure")

    def succeeds(event, ctx) -> None:
        calls.append("three")

    bus.subscribe(_EventA, fail_one)
    bus.subscribe(_EventA, fail_two)
    bus.subscribe(_EventA, succeeds)

    with caplog.at_level(logging.ERROR):
        bus.publish(_EventA(), context)

    assert calls == ["one", "two", "three"]
    failure_records = [r for r in caplog.records if "Post-commit handler failed" in r.message]
    assert len(failure_records) == 2


def test_re_entrant_publication_is_breadth_first(bus, context) -> None:
    """A handler for EventA that itself publishes EventB must see EventB's handlers run only
    after ALL of EventA's own handlers have completed -- deliberately breadth-first, not the
    legacy Signal's depth-first-under-recursion (ADR-005 Sec8)."""
    order: list[str] = []

    def a_first(event, ctx) -> None:
        order.append("A1")
        bus.publish(_EventB(), ctx)

    def a_second(event, ctx) -> None:
        order.append("A2")

    def b_handler(event, ctx) -> None:
        order.append("B1")

    bus.subscribe(_EventA, a_first)
    bus.subscribe(_EventA, a_second)
    bus.subscribe(_EventB, b_handler)

    bus.publish(_EventA(), context)

    assert order == ["A1", "A2", "B1"], (
        f"expected breadth-first order [A1, A2, B1], got {order}"
    )


def test_context_is_propagated_unchanged_through_re_entrant_publication(bus) -> None:
    contexts_seen: list[DomainEventContext] = []
    context = DomainEventContext(correlation_id="corr-xyz", causation_id="cause-1")

    def a_handler(event, ctx) -> None:
        contexts_seen.append(ctx)
        bus.publish(_EventB(), ctx)

    def b_handler(event, ctx) -> None:
        contexts_seen.append(ctx)

    bus.subscribe(_EventA, a_handler)
    bus.subscribe(_EventB, b_handler)

    bus.publish(_EventA(), context)

    assert contexts_seen == [context, context]


def test_queue_and_dispatching_flag_are_empty_after_top_level_publish_completes(bus, context) -> None:
    bus.subscribe(_EventA, lambda e, c: None)

    bus.publish(_EventA(), context)

    assert len(bus._queue) == 0
    assert bus._dispatching is False


def test_no_queue_state_leaks_between_independent_top_level_publishes(bus, context) -> None:
    seen: list[str] = []
    bus.subscribe(_EventA, lambda e, c: seen.append("a"))

    bus.publish(_EventA(), context)
    bus.publish(_EventA(), context)

    assert seen == ["a", "a"]
    assert len(bus._queue) == 0


def test_handler_registry_snapshot_is_lock_consistent_with_concurrent_subscribe(bus, context) -> None:
    """A subscribe() call arriving after a dispatch's snapshot was already taken must not be
    observed mid-iteration for that same publish() call, but is picked up on the next one."""
    seen: list[str] = []

    def first(event, ctx) -> None:
        seen.append("first")
        bus.subscribe(_EventA, lambda e, c: seen.append("added-during-dispatch"))

    bus.subscribe(_EventA, first)

    bus.publish(_EventA(), context)
    assert seen == ["first"], "a handler added during dispatch must not run in that same publish"

    bus.publish(_EventA(), context)
    assert seen == ["first", "first", "added-during-dispatch"]


def test_subscription_dispose_removes_the_handler(bus, context) -> None:
    calls: list[str] = []
    subscription = bus.subscribe(_EventA, lambda e, c: calls.append("hit"))

    subscription.dispose()
    bus.publish(_EventA(), context)

    assert calls == []


def test_subscription_dispose_is_idempotent(bus, context) -> None:
    subscription = bus.subscribe(_EventA, lambda e, c: None)
    subscription.dispose()
    subscription.dispose()  # must not raise


def test_disposing_one_subscription_does_not_affect_an_independent_identical_subscription(
    bus, context
) -> None:
    calls: list[str] = []

    def handler(event, ctx) -> None:
        calls.append("hit")

    first_subscription = bus.subscribe(_EventA, handler)
    bus.subscribe(_EventA, handler)

    first_subscription.dispose()
    bus.publish(_EventA(), context)

    assert calls == ["hit"]


def test_two_threads_publishing_concurrently_do_not_corrupt_the_queue_or_double_dispatch(context) -> None:
    """Two threads calling publish() concurrently must not corrupt the internal queue or
    cause a handler to run more times than events were actually published."""
    bus = InProcessPostCommitEventBus()
    call_count = {"n": 0}
    lock = threading.Lock()

    def handler(event, ctx) -> None:
        with lock:
            call_count["n"] += 1

    bus.subscribe(_EventA, handler)

    def publish_many() -> None:
        for _ in range(200):
            bus.publish(_EventA(), context)

    thread_1 = threading.Thread(target=publish_many)
    thread_2 = threading.Thread(target=publish_many)
    thread_1.start()
    thread_2.start()
    thread_1.join(timeout=10)
    thread_2.join(timeout=10)

    assert call_count["n"] == 400
    assert len(bus._queue) == 0
    assert bus._dispatching is False


def test_empty_queue_dispatching_flip_race_is_closed(context) -> None:
    """Adversarial test forcing the exact interleaving the original race required: a
    publish() arriving at the precise moment a drain loop is checking "is the queue empty"
    must never be stranded -- it either gets picked up by the in-progress drain, or
    `_dispatching` has genuinely already flipped back to False and the new publish() starts
    its own drain. Forced by having the last handler invocation block until a second thread's
    publish() call has entered its own critical section.
    """
    bus = InProcessPostCommitEventBus()
    received: list[str] = []
    handler_started = threading.Event()
    late_publish_done = threading.Event()

    def slow_handler(event, ctx) -> None:
        received.append("slow")
        handler_started.set()
        # Give the racing publish() a real chance to reach its own critical section while
        # this drain loop is mid-flight (about to re-check the queue).
        late_publish_done.wait(timeout=2)

    def late_handler(event, ctx) -> None:
        received.append("late")

    bus.subscribe(_EventA, slow_handler)
    bus.subscribe(_EventB, late_handler)

    def racing_publish() -> None:
        handler_started.wait(timeout=2)
        bus.publish(_EventB(), context)
        late_publish_done.set()

    racer = threading.Thread(target=racing_publish)
    racer.start()
    bus.publish(_EventA(), context)
    racer.join(timeout=5)

    assert "slow" in received
    assert "late" in received, "the racing publish() must never be stranded in the queue"
    assert len(bus._queue) == 0
    assert bus._dispatching is False
