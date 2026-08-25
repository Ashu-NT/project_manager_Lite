"""ADR-005 §11: integration-event/outbox atomicity foundation.

This does NOT modify or re-test ADR-PF-011's real outbox implementation
(`IntegrationEventEnvelope`, `IntegrationOutboxService`, delivery/retry/dead-letter logic) --
those are untouched. This proves only the transactional *mechanism* P3 provides: a
transactional handler that stages an outbox-like row participates in the exact same database
transaction as the business mutation, using a minimal, test-only table -- never a real module's
outbox producer.

Per ADR-005 §11, the correct shape is:

    business mutation -> DomainEvent -> transactional handler stages an outbox-like row
    (same Session, same open transaction) -> uow.commit() persists both together

never:

    uow.commit() -> PostCommitEventPublisher -> create outbox row

which would let a rolled-back transaction still be paired with a durable message.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, select, text

from src.core.shared.events.aggregate_events import RecordsDomainEvents
from src.core.shared.events.domain_event_context import DomainEventContext

_metadata = MetaData()

_business_row_table = Table(
    "business_row",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
)

_outbox_like_table = Table(
    "outbox_like",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("event_type", String),
)


@pytest.fixture(autouse=True)
def _create_schema(session_factory) -> None:
    engine = session_factory.kw["bind"]
    _metadata.create_all(engine)


def _context() -> DomainEventContext:
    return DomainEventContext(correlation_id="corr-outbox")


@dataclass(frozen=True, slots=True)
class _SomeBusinessFact:
    occurred_at: datetime = datetime.now(timezone.utc)


class _SomeAggregate(RecordsDomainEvents):
    pass


def _read_row_counts(session_factory) -> tuple[int, int]:
    verification_session = session_factory()
    try:
        business_count = verification_session.execute(
            select(_business_row_table)
        ).fetchall()
        outbox_count = verification_session.execute(select(_outbox_like_table)).fetchall()
        return len(business_count), len(outbox_count)
    finally:
        verification_session.close()


def test_business_row_and_outbox_like_row_commit_together(
    uow_factory, transactional_dispatcher, session_factory
) -> None:
    def stage_business_and_outbox_rows(event, uow) -> None:
        # A real module's transactional handler would use its own module-specific
        # UnitOfWork extension's typed accessors here (P4+); this test proxies that with
        # direct, same-session Core statements to prove the transaction boundary itself,
        # without inventing any real business-module infrastructure in P3.
        uow._session.execute(_business_row_table.insert().values(id=1, name="widget"))
        uow._session.execute(
            _outbox_like_table.insert().values(id=1, event_type="_SomeBusinessFact")
        )

    transactional_dispatcher.subscribe(_SomeBusinessFact, stage_business_and_outbox_rows)

    with uow_factory.create(context=_context()) as uow:
        aggregate = _SomeAggregate()
        aggregate._record_event(_SomeBusinessFact())
        uow.register_touched(aggregate)
        uow.commit()

    business_count, outbox_count = _read_row_counts(session_factory)
    assert business_count == 1
    assert outbox_count == 1


def test_business_row_and_outbox_like_row_both_roll_back_together_on_handler_failure(
    uow_factory, transactional_dispatcher, session_factory
) -> None:
    def stage_then_fail(event, uow) -> None:
        uow._session.execute(_business_row_table.insert().values(id=2, name="rejected-widget"))
        uow._session.execute(
            _outbox_like_table.insert().values(id=2, event_type="_SomeBusinessFact")
        )
        raise ValueError("a later validation step in the same handler rejects this mutation")

    transactional_dispatcher.subscribe(_SomeBusinessFact, stage_then_fail)

    with pytest.raises(ValueError):
        with uow_factory.create(context=_context()) as uow:
            aggregate = _SomeAggregate()
            aggregate._record_event(_SomeBusinessFact())
            uow.register_touched(aggregate)
            uow.commit()

    business_count, outbox_count = _read_row_counts(session_factory)
    assert business_count == 0, "the business row must not survive the rollback"
    assert outbox_count == 0, "the outbox-like row must not survive the rollback either"


def test_business_row_and_outbox_like_row_both_roll_back_on_database_commit_failure(
    uow_factory, transactional_dispatcher, session_factory
) -> None:
    """Even if every transactional handler succeeds, a downstream database commit failure
    (e.g. a constraint violation flushed at commit time) must still roll back BOTH rows
    together -- staging succeeding is not the same guarantee as committing succeeding."""

    def stage_duplicate_outbox_id(event, uow) -> None:
        uow._session.execute(_business_row_table.insert().values(id=3, name="widget-3"))
        # A duplicate primary key is flushed lazily -- this raises only once the session
        # actually tries to persist it, which happens inside commit()'s own session.commit()
        # call, not here at staging time.
        uow._session.execute(
            _outbox_like_table.insert().values(id=3, event_type="_SomeBusinessFact")
        )
        uow._session.execute(
            _outbox_like_table.insert().values(id=3, event_type="duplicate-primary-key")
        )

    transactional_dispatcher.subscribe(_SomeBusinessFact, stage_duplicate_outbox_id)

    with pytest.raises(Exception):  # a SQLAlchemy IntegrityError subclass, not asserted by type here
        with uow_factory.create(context=_context()) as uow:
            aggregate = _SomeAggregate()
            aggregate._record_event(_SomeBusinessFact())
            uow.register_touched(aggregate)
            uow.commit()

    business_count, outbox_count = _read_row_counts(session_factory)
    assert business_count == 0, "a downstream commit failure must roll back the business row too"
    assert outbox_count == 0
