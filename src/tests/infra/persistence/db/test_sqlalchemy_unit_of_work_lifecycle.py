"""ADR-005 §9: `SqlAlchemyUnitOfWorkBase` -- fresh session ownership, context-manager
semantics, and lifecycle misuse.
"""

from __future__ import annotations

import logging

import pytest
from sqlalchemy import text

from src.core.shared.persistence.unit_of_work import UnitOfWorkClosedError
from src.core.shared.events.domain_event_context import DomainEventContext


def _context(correlation_id: str = "corr-1") -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# Fresh session ownership (item 7)
# ---------------------------------------------------------------------------


def test_two_create_calls_open_genuinely_different_session_objects(uow_factory) -> None:
    uow1 = uow_factory.create(context=_context("c1"))
    uow2 = uow_factory.create(context=_context("c2"))

    assert uow1._session is not uow2._session


def test_two_independent_unit_of_works_do_not_share_uncommitted_identity_map_state(
    uow_factory, session_factory
) -> None:
    """Staging a change in one UoW's session must not be visible to a second, independent
    UoW's session until the first one actually commits."""
    engine = session_factory.kw["bind"]
    with engine.connect() as setup_connection:
        setup_connection.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)"))
        setup_connection.commit()

    uow1 = uow_factory.create(context=_context("c1"))
    uow2 = uow_factory.create(context=_context("c2"))

    uow1._session.execute(text("INSERT INTO probe (id, value) VALUES (1, 'from-uow1')"))
    # Not committed yet -- uow2's own session, on its own connection, must not see it.
    visible_to_uow2 = uow2._session.execute(text("SELECT COUNT(*) FROM probe")).scalar()
    assert visible_to_uow2 == 0

    uow1._session.rollback()
    uow1._session.close()
    uow2._session.close()


def test_rollback_in_one_unit_of_work_does_not_roll_back_a_sibling(uow_factory, session_factory) -> None:
    engine = session_factory.kw["bind"]
    with engine.connect() as setup_connection:
        setup_connection.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)"))
        setup_connection.commit()

    committed_uow = uow_factory.create(context=_context("committed"))
    committed_uow._session.execute(text("INSERT INTO probe (id, value) VALUES (1, 'kept')"))
    committed_uow._session.commit()
    committed_uow._session.close()

    rolled_back_uow = uow_factory.create(context=_context("rolled-back"))
    rolled_back_uow._session.execute(text("INSERT INTO probe (id, value) VALUES (2, 'discarded')"))
    rolled_back_uow._session.rollback()
    rolled_back_uow._session.close()

    verification_uow = uow_factory.create(context=_context("verify"))
    rows = verification_uow._session.execute(text("SELECT id, value FROM probe")).fetchall()
    verification_uow._session.close()

    assert [tuple(row) for row in rows] == [(1, "kept")]


def test_closing_one_unit_of_work_does_not_close_a_sibling(uow_factory) -> None:
    uow1 = uow_factory.create(context=_context("c1"))
    uow2 = uow_factory.create(context=_context("c2"))

    with uow1:
        uow1.commit()

    assert uow1._closed is True
    assert uow2._closed is False
    uow2._session.close()


def test_no_process_global_session_is_used(uow_factory) -> None:
    """Confirms the factory's session_factory is actually invoked per create() call,
    never returning a cached/shared Session."""
    sessions = [uow_factory.create(context=_context(f"c{i}"))._session for i in range(5)]
    assert len({id(s) for s in sessions}) == 5
    for session in sessions:
        session.close()


# ---------------------------------------------------------------------------
# Context manager semantics (items 8, 25)
# ---------------------------------------------------------------------------


def test_enter_returns_self(uow_factory) -> None:
    uow = uow_factory.create(context=_context())
    with uow as entered:
        assert entered is uow
        uow.commit()


def test_clean_exit_after_commit_does_nothing_further(uow_factory) -> None:
    with uow_factory.create(context=_context()) as uow:
        uow.commit()
    assert uow._closed is True
    assert uow._committed is True


def test_exception_before_commit_rolls_back_and_closes(uow_factory) -> None:
    with pytest.raises(ValueError):
        with uow_factory.create(context=_context()) as uow:
            raise ValueError("something failed before commit was reached")

    assert uow._closed is True
    assert uow._committed is False


def test_exiting_cleanly_without_ever_calling_commit_closes_without_committing(uow_factory, caplog) -> None:
    """ADR-005 Sec9 leaves this specific case (no exception, but commit() never reached)
    unaddressed by its literal text -- resolved as a documented safety net (close, do not
    commit) rather than silently leaking an open Session. See the P3 report for this
    resolution."""
    with caplog.at_level(logging.WARNING):
        with uow_factory.create(context=_context()) as uow:
            pass  # deliberately never call commit()

    assert uow._closed is True
    assert uow._committed is False
    assert any("without commit()" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Lifecycle misuse (item 26)
# ---------------------------------------------------------------------------


def test_commit_twice_raises_unit_of_work_closed_error(uow_factory) -> None:
    with uow_factory.create(context=_context()) as uow:
        uow.commit()

    with pytest.raises(UnitOfWorkClosedError):
        uow.commit()


def test_commit_after_an_unrelated_later_exception_does_not_attempt_a_meaningless_rollback(
    uow_factory,
) -> None:
    """Once commit() has already succeeded and closed everything, a later, unrelated
    exception inside the same `with` block must not try to roll back an already-committed,
    already-closed transaction -- there is nothing left to roll back."""
    with pytest.raises(RuntimeError, match="unrelated failure after commit"):
        with uow_factory.create(context=_context()) as uow:
            uow.commit()
            raise RuntimeError("unrelated failure after commit")

    assert uow._committed is True
    assert uow._closed is True


def test_using_unit_of_work_after_close_raises_unit_of_work_closed_error(uow_factory) -> None:
    with uow_factory.create(context=_context()) as uow:
        uow.commit()

    with pytest.raises(UnitOfWorkClosedError):
        uow.record_event(object())


def test_tracked_aggregates_remains_readable_after_rollback_for_inspection(uow_factory) -> None:
    """ADR-005 Sec9's rollback-safety rule: pending events/aggregates may remain available
    for inspection after a rollback -- tracked_aggregates() is not closed-checked."""
    from dataclasses import dataclass
    from datetime import datetime, timezone

    from src.core.shared.events.aggregate_events import RecordsDomainEvents

    class _Agg(RecordsDomainEvents):
        pass

    with pytest.raises(ValueError):
        with uow_factory.create(context=_context()) as uow:
            agg = _Agg()
            uow.register_touched(agg)
            raise ValueError("boom")

    assert len(uow.tracked_aggregates()) == 1  # still inspectable, not closed-checked
