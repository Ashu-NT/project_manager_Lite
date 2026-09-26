"""SQLite allows only one writer at a time for the whole database file, even
in WAL mode. This app opens a fresh, independent Session/connection per
UnitOfWork, so two commands committed close together race for that single
writer slot and can surface as `sqlite3.OperationalError: database is
locked` (see e.g. an Organization update racing an Employee create, each
committing its own activity-entry insert). `_write_lock_for()` in
unit_of_work.py serializes SQLite commits in-process to remove that race;
Postgres (also supported) must be unaffected since it handles concurrent
writers natively."""

from __future__ import annotations

import threading
import time
from contextlib import AbstractContextManager

from src.infra.persistence.db.unit_of_work import _SQLITE_WRITE_LOCK, _write_lock_for


class _FakeDialect:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeBind:
    def __init__(self, dialect_name: str) -> None:
        self.dialect = _FakeDialect(dialect_name)


class _FakeSession:
    def __init__(self, dialect_name: str) -> None:
        self._bind = _FakeBind(dialect_name)

    def get_bind(self):
        return self._bind


def test_sqlite_session_gets_the_shared_write_lock() -> None:
    lock = _write_lock_for(_FakeSession("sqlite"))
    assert lock is _SQLITE_WRITE_LOCK


def test_postgres_session_gets_a_no_op_lock() -> None:
    lock = _write_lock_for(_FakeSession("postgresql"))
    assert lock is not _SQLITE_WRITE_LOCK
    assert isinstance(lock, AbstractContextManager)
    # Must never block -- Postgres handles its own concurrent writers.
    with lock:
        pass


def test_session_with_no_bind_falls_back_to_a_no_op_lock() -> None:
    class _UnboundSession:
        def get_bind(self):
            raise RuntimeError("not bound")

    lock = _write_lock_for(_UnboundSession())
    assert lock is not _SQLITE_WRITE_LOCK
    with lock:
        pass


def test_sqlite_write_lock_serializes_two_concurrent_commits() -> None:
    """Two 'commits' that overlap in wall-clock time must not run their
    critical sections concurrently -- the second must wait for the first to
    fully release the lock before starting, exactly what prevents the
    Organization-update/Employee-create race from reaching SQLite as two
    simultaneous writers."""
    events: list[str] = []
    lock_a = _write_lock_for(_FakeSession("sqlite"))
    lock_b = _write_lock_for(_FakeSession("sqlite"))
    assert lock_a is lock_b  # same shared lock regardless of which session asks

    start_barrier = threading.Barrier(2)

    def slow_commit() -> None:
        start_barrier.wait()
        with lock_a:
            events.append("A-start")
            time.sleep(0.2)
            events.append("A-end")

    def fast_commit() -> None:
        start_barrier.wait()
        time.sleep(0.05)  # ensure A has already entered the critical section
        with lock_b:
            events.append("B-start")

    t1 = threading.Thread(target=slow_commit)
    t2 = threading.Thread(target=fast_commit)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert events == ["A-start", "A-end", "B-start"], (
        "B must not start until A has fully released the write lock"
    )
