"""ADR-005 §9/§10: `SqlAlchemyUnitOfWorkBase` -- transactional dispatch integration, commit/
rollback behavior, dynamic multi-round event re-collection, the `MAX_DISPATCH_ROUNDS` cycle
guard, `record_event()`, and event loss/duplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.core.shared.events.aggregate_events import RecordsDomainEvents
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.persistence.unit_of_work import MaxDispatchRoundsExceededError
from src.infra.persistence.db.unit_of_work import MAX_DISPATCH_ROUNDS


def _context(correlation_id: str = "corr-1") -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


@dataclass(frozen=True, slots=True)
class _EventA:
    occurred_at: datetime = datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _EventB:
    occurred_at: datetime = datetime.now(timezone.utc)


class _AggregateA(RecordsDomainEvents):
    pass


class _AggregateB(RecordsDomainEvents):
    pass


# ---------------------------------------------------------------------------
# Successful transaction (item 35)
# ---------------------------------------------------------------------------


def test_successful_transaction_dispatches_before_commit_and_publishes_after(
    uow_factory, transactional_dispatcher, post_commit_bus
) -> None:
    order: list[str] = []
    transactional_dispatcher.subscribe(_EventA, lambda e, u: order.append("transactional"))
    post_commit_bus.subscribe(_EventA, lambda e, c: order.append("post-commit"))

    with uow_factory.create(context=_context("corr-xyz")) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.commit()

    assert order == ["transactional", "post-commit"]
    assert uow._committed is True
    assert uow._closed is True


def test_post_commit_handler_receives_the_same_context_the_uow_was_created_with(
    uow_factory, post_commit_bus
) -> None:
    received_contexts: list[DomainEventContext] = []
    post_commit_bus.subscribe(_EventA, lambda e, c: received_contexts.append(c))

    context = _context("corr-preserved")
    with uow_factory.create(context=context) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.commit()

    assert received_contexts == [context]


def test_transactional_handler_receives_the_exact_same_uow_instance(
    uow_factory, transactional_dispatcher
) -> None:
    received_uows: list[object] = []
    transactional_dispatcher.subscribe(_EventA, lambda e, u: received_uows.append(u))

    with uow_factory.create(context=_context()) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.commit()

    assert received_uows == [uow]


# ---------------------------------------------------------------------------
# Transactional handler failure (item 36)
# ---------------------------------------------------------------------------


def test_transactional_handler_failure_rolls_back_and_never_publishes(
    uow_factory, transactional_dispatcher, post_commit_bus
) -> None:
    calls: list[str] = []

    def first_handler(event, uow) -> None:
        calls.append("first")

    def second_handler_raises(event, uow) -> None:
        calls.append("second")
        raise ValueError("business rule violated")

    def third_handler_never_runs(event, uow) -> None:
        calls.append("third")

    transactional_dispatcher.subscribe(_EventA, first_handler)
    transactional_dispatcher.subscribe(_EventA, second_handler_raises)
    transactional_dispatcher.subscribe(_EventA, third_handler_never_runs)

    post_commit_received: list[object] = []
    post_commit_bus.subscribe(_EventA, lambda e, c: post_commit_received.append(e))

    with pytest.raises(ValueError, match="business rule violated"):
        with uow_factory.create(context=_context()) as uow:
            aggregate = _AggregateA()
            aggregate._record_event(_EventA())
            uow.register_touched(aggregate)
            uow.commit()

    assert calls == ["first", "second"], "third handler must not run once the second raised"
    assert post_commit_received == [], "post-commit must never run when a transactional handler fails"
    assert uow._committed is False
    assert uow._closed is True


# ---------------------------------------------------------------------------
# Commit (database) failure (item 37)
# ---------------------------------------------------------------------------


def test_database_commit_failure_rolls_back_and_never_publishes(
    uow_factory, transactional_dispatcher, post_commit_bus
) -> None:
    transactional_ran: list[str] = []
    transactional_dispatcher.subscribe(_EventA, lambda e, u: transactional_ran.append("ran"))

    post_commit_received: list[object] = []
    post_commit_bus.subscribe(_EventA, lambda e, c: post_commit_received.append(e))

    class _SimulatedCommitFailure(Exception):
        pass

    with pytest.raises(_SimulatedCommitFailure):
        with uow_factory.create(context=_context()) as uow:
            aggregate = _AggregateA()
            aggregate._record_event(_EventA())
            uow.register_touched(aggregate)

            def _raise_on_commit() -> None:
                raise _SimulatedCommitFailure("database commit failed")

            uow._session.commit = _raise_on_commit  # simulate a real DB commit failure
            uow.commit()

    assert transactional_ran == ["ran"], "transactional handlers may have already run"
    assert post_commit_received == [], "post-commit publication must never occur after a commit failure"
    assert uow._committed is False, "a failed commit must never report success"
    assert uow._closed is True


# ---------------------------------------------------------------------------
# Post-commit failure does not change the commit result (item 38)
# ---------------------------------------------------------------------------


def test_post_commit_handler_failure_does_not_undo_the_committed_transaction(
    uow_factory, post_commit_bus, caplog
) -> None:
    import logging

    calls: list[str] = []

    def failing_handler(event, context) -> None:
        calls.append("failing")
        raise RuntimeError("post-commit adapter bug")

    def healthy_handler(event, context) -> None:
        calls.append("healthy")

    post_commit_bus.subscribe(_EventA, failing_handler)
    post_commit_bus.subscribe(_EventA, healthy_handler)

    with caplog.at_level(logging.ERROR):
        with uow_factory.create(context=_context()) as uow:
            aggregate = _AggregateA()
            aggregate._record_event(_EventA())
            uow.register_touched(aggregate)
            uow.commit()  # must not raise -- ISOLATE_AND_CONTINUE, handled entirely by P2's bus

    assert calls == ["failing", "healthy"]
    assert uow._committed is True, "the business transaction remains committed"
    assert uow._closed is True
    assert any("Post-commit handler failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Multi-round dynamic event re-collection (item 39)
# ---------------------------------------------------------------------------


def test_a_transactional_handler_touching_a_second_aggregate_is_discovered_and_dispatched(
    uow_factory, transactional_dispatcher
) -> None:
    """The exact motivating scenario ADR-005 Sec10 describes: a handler for EventA loads or
    creates Aggregate B, which itself records EventB -- EventB must be discovered and
    dispatched in a later round, not silently dropped."""
    order: list[str] = []

    def handle_a(event, uow) -> None:
        order.append("A")
        aggregate_b = _AggregateB()
        aggregate_b._record_event(_EventB())
        uow.register_touched(aggregate_b)

    def handle_b(event, uow) -> None:
        order.append("B")

    transactional_dispatcher.subscribe(_EventA, handle_a)
    transactional_dispatcher.subscribe(_EventB, handle_b)

    with uow_factory.create(context=_context()) as uow:
        aggregate_a = _AggregateA()
        aggregate_a._record_event(_EventA())
        uow.register_touched(aggregate_a)
        uow.commit()

    assert order == ["A", "B"]


def test_multiple_rounds_of_re_collection_all_complete_before_commit(
    uow_factory, transactional_dispatcher
) -> None:
    """Three genuine rounds: A -> B -> C, each discovered only after the previous round's
    handler runs."""

    @dataclass(frozen=True, slots=True)
    class _EventC:
        occurred_at: datetime = datetime.now(timezone.utc)

    class _AggregateC(RecordsDomainEvents):
        pass

    order: list[str] = []

    def handle_a(event, uow) -> None:
        order.append("A")
        aggregate_b = _AggregateB()
        aggregate_b._record_event(_EventB())
        uow.register_touched(aggregate_b)

    def handle_b(event, uow) -> None:
        order.append("B")
        aggregate_c = _AggregateC()
        aggregate_c._record_event(_EventC())
        uow.register_touched(aggregate_c)

    def handle_c(event, uow) -> None:
        order.append("C")

    transactional_dispatcher.subscribe(_EventA, handle_a)
    transactional_dispatcher.subscribe(_EventB, handle_b)
    transactional_dispatcher.subscribe(_EventC, handle_c)

    with uow_factory.create(context=_context()) as uow:
        aggregate_a = _AggregateA()
        aggregate_a._record_event(_EventA())
        uow.register_touched(aggregate_a)
        uow.commit()

    assert order == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Cycle guard (item 40)
# ---------------------------------------------------------------------------


def test_a_deterministic_cycle_raises_max_dispatch_rounds_exceeded_and_rolls_back(
    uow_factory, transactional_dispatcher, post_commit_bus
) -> None:
    def cycle_via_a(event, uow) -> None:
        aggregate_b = _AggregateB()
        aggregate_b._record_event(_EventB())
        uow.register_touched(aggregate_b)

    def cycle_via_b(event, uow) -> None:
        aggregate_a = _AggregateA()
        aggregate_a._record_event(_EventA())  # a genuinely NEW event object every round
        uow.register_touched(aggregate_a)

    transactional_dispatcher.subscribe(_EventA, cycle_via_a)
    transactional_dispatcher.subscribe(_EventB, cycle_via_b)

    post_commit_received: list[object] = []
    post_commit_bus.subscribe(_EventA, lambda e, c: post_commit_received.append(e))

    with pytest.raises(MaxDispatchRoundsExceededError, match=str(MAX_DISPATCH_ROUNDS)):
        with uow_factory.create(context=_context()) as uow:
            aggregate_a = _AggregateA()
            aggregate_a._record_event(_EventA())
            uow.register_touched(aggregate_a)
            uow.commit()

    assert post_commit_received == [], "no post-commit publication when the cycle guard fires"
    assert uow._committed is False
    assert uow._closed is True


def test_normal_multi_round_chain_well_under_the_round_limit_succeeds(
    uow_factory, transactional_dispatcher
) -> None:
    """A sanity check that the round limit doesn't trigger for entirely ordinary chains --
    only genuine, unbounded cycles should ever hit MAX_DISPATCH_ROUNDS."""
    calls = {"count": 0}

    def handle_a(event, uow) -> None:
        calls["count"] += 1

    transactional_dispatcher.subscribe(_EventA, handle_a)

    with uow_factory.create(context=_context()) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.commit()  # must not raise

    assert calls["count"] == 1


# ---------------------------------------------------------------------------
# record_event() escape hatch (item 41)
# ---------------------------------------------------------------------------


def test_record_event_stages_an_application_authored_event_with_no_aggregate_owner(
    uow_factory, transactional_dispatcher, post_commit_bus
) -> None:
    """A genuinely orchestration-level fact, staged via record_event(), participates in the
    exact same transactional-then-post-commit lifecycle as an aggregate-recorded event, and
    is preserved in its own right rather than requiring a fake aggregate to own it."""
    transactional_seen: list[object] = []
    post_commit_seen: list[tuple[object, DomainEventContext]] = []
    transactional_dispatcher.subscribe(_EventA, lambda e, u: transactional_seen.append(e))
    post_commit_bus.subscribe(_EventA, lambda e, c: post_commit_seen.append((e, c)))

    context = _context("corr-orchestration")
    event = _EventA()
    with uow_factory.create(context=context) as uow:
        uow.record_event(event)  # no aggregate at all -- this IS the orchestration path
        uow.commit()

    assert transactional_seen == [event]
    assert post_commit_seen == [(event, context)]


def test_record_event_and_aggregate_recorded_events_both_participate_in_one_drain(
    uow_factory, transactional_dispatcher
) -> None:
    order: list[str] = []
    transactional_dispatcher.subscribe(_EventA, lambda e, u: order.append("aggregate-recorded"))
    transactional_dispatcher.subscribe(_EventB, lambda e, u: order.append("manually-recorded"))

    with uow_factory.create(context=_context()) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.record_event(_EventB())
        uow.commit()

    assert set(order) == {"aggregate-recorded", "manually-recorded"}


# ---------------------------------------------------------------------------
# Event loss / duplication (item 42)
# ---------------------------------------------------------------------------


def test_an_event_is_dispatched_exactly_once_per_commit(uow_factory, transactional_dispatcher) -> None:
    call_count = {"n": 0}
    transactional_dispatcher.subscribe(_EventA, lambda e, u: call_count.__setitem__("n", call_count["n"] + 1))

    with uow_factory.create(context=_context()) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.commit()

    assert call_count["n"] == 1


def test_events_from_a_previous_unit_of_work_never_leak_into_the_next(
    uow_factory, transactional_dispatcher
) -> None:
    received: list[object] = []
    transactional_dispatcher.subscribe(_EventA, lambda e, u: received.append(e))

    with uow_factory.create(context=_context("first")) as first_uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        first_uow.register_touched(aggregate)
        first_uow.commit()

    assert len(received) == 1

    # A second, independent UnitOfWork with no events recorded must dispatch nothing.
    with uow_factory.create(context=_context("second")) as second_uow:
        second_uow.commit()

    assert len(received) == 1, "the second, empty UnitOfWork must not re-dispatch the first one's event"


def test_rollback_does_not_later_cause_stale_event_publication(
    uow_factory, transactional_dispatcher, post_commit_bus
) -> None:
    post_commit_received: list[object] = []
    post_commit_bus.subscribe(_EventA, lambda e, c: post_commit_received.append(e))

    def fails(event, uow) -> None:
        raise ValueError("rejected")

    transactional_dispatcher.subscribe(_EventA, fails)

    with pytest.raises(ValueError):
        with uow_factory.create(context=_context()) as uow:
            aggregate = _AggregateA()
            aggregate._record_event(_EventA())
            uow.register_touched(aggregate)
            uow.commit()

    # Nothing about the rolled-back UoW's events is ever published later -- there is no
    # deferred/retry mechanism in this base class that could resurrect them.
    assert post_commit_received == []


def test_post_commit_bus_queue_remains_clean_after_a_uow_commit(uow_factory, post_commit_bus) -> None:
    with uow_factory.create(context=_context()) as uow:
        aggregate = _AggregateA()
        aggregate._record_event(_EventA())
        uow.register_touched(aggregate)
        uow.commit()

    assert len(post_commit_bus._queue) == 0
    assert post_commit_bus._dispatching is False
