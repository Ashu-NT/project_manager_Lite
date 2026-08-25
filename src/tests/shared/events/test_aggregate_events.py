"""ADR-005 §6: `RecordsDomainEvents` -- minimal aggregate event-recording mixin.

Framework-independent by construction: these tests never import UnitOfWork, a dispatcher, a
publisher, SQLAlchemy, or anything UI-related, because RecordsDomainEvents must not know about
any of them (ADR-005 §6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.shared.events.aggregate_events import RecordsDomainEvents


@dataclass(frozen=True, slots=True, kw_only=True)
class _FakeEvent:
    occurred_at: datetime
    label: str = ""


class _FakeAggregate(RecordsDomainEvents):
    pass


def test_domain_events_starts_empty() -> None:
    aggregate = _FakeAggregate()
    assert aggregate.domain_events() == ()


def test_record_event_appends_and_domain_events_returns_in_recorded_order() -> None:
    aggregate = _FakeAggregate()
    now = datetime.now(timezone.utc)
    first = _FakeEvent(occurred_at=now, label="first")
    second = _FakeEvent(occurred_at=now, label="second")

    aggregate._record_event(first)
    aggregate._record_event(second)

    assert aggregate.domain_events() == (first, second)


def test_domain_events_is_a_read_only_snapshot_and_does_not_clear() -> None:
    aggregate = _FakeAggregate()
    event = _FakeEvent(occurred_at=datetime.now(timezone.utc))
    aggregate._record_event(event)

    snapshot_1 = aggregate.domain_events()
    snapshot_2 = aggregate.domain_events()

    assert snapshot_1 == snapshot_2 == (event,)
    assert isinstance(snapshot_1, tuple), "must be a tuple, never the live mutable list itself"


def test_clear_domain_events_empties_pending_events() -> None:
    aggregate = _FakeAggregate()
    aggregate._record_event(_FakeEvent(occurred_at=datetime.now(timezone.utc)))

    aggregate.clear_domain_events()

    assert aggregate.domain_events() == ()


def test_clear_domain_events_is_idempotent_on_an_already_empty_aggregate() -> None:
    aggregate = _FakeAggregate()
    aggregate.clear_domain_events()  # never recorded anything -- must not raise
    assert aggregate.domain_events() == ()


def test_two_aggregate_instances_do_not_share_a_mutable_event_list() -> None:
    """Guards against the classic mutable-default-shared-across-instances bug -- each
    aggregate's _pending_domain_events must be its own list, lazily created per instance."""
    first_aggregate = _FakeAggregate()
    second_aggregate = _FakeAggregate()

    first_aggregate._record_event(_FakeEvent(occurred_at=datetime.now(timezone.utc), label="only-first"))

    assert first_aggregate.domain_events() != ()
    assert second_aggregate.domain_events() == (), (
        "recording an event on one aggregate must never be visible on a sibling instance"
    )


def test_clearing_one_aggregate_does_not_affect_a_sibling_aggregate() -> None:
    first_aggregate = _FakeAggregate()
    second_aggregate = _FakeAggregate()
    now = datetime.now(timezone.utc)

    first_aggregate._record_event(_FakeEvent(occurred_at=now, label="a"))
    second_aggregate._record_event(_FakeEvent(occurred_at=now, label="b"))

    first_aggregate.clear_domain_events()

    assert first_aggregate.domain_events() == ()
    assert second_aggregate.domain_events() != ()
