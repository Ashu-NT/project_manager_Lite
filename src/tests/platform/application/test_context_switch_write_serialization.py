"""Regression coverage for a live "database is locked" incident: switching
the active organization/tenant commits directly on the one long-lived
Session the composition root shares across the process (see app.py and
context_switch_service.commit_context_switch), rather than through a
per-operation UnitOfWork. Because every entity mutation (Employee, Document,
Site, ...) commits its own independent UnitOfWork, an unserialized commit on
that shared session could race one of those for SQLite's single writer slot
and surface as `sqlite3.OperationalError: database is locked` -- observed in
production on an unrelated entity's activity-entry insert while the user was
switching organizations. commit_context_switch must take the same process
lock a UnitOfWork.commit() takes."""

from __future__ import annotations

import threading
import time

from src.infra.persistence.db.unit_of_work import _SQLITE_WRITE_LOCK, sqlite_write_lock


def test_commit_context_switch_waits_for_the_shared_sqlite_write_lock(services) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]

    target_org = organization_service.create_organization(
        organization_code="CTXSWITCH-TARGET", display_name="Context Switch Target Org"
    )

    events: list[str] = []
    lock_acquired = threading.Event()

    def hold_lock_like_a_concurrent_unit_of_work_commit() -> None:
        # Deliberately touches no DB state -- the fixture's SQLite session
        # is thread-affined, so the real "concurrent commit" side of this
        # test is simulated by holding the same shared lock a UnitOfWork
        # commit would hold, not by running a second UnitOfWork off-thread.
        with _SQLITE_WRITE_LOCK:
            events.append("uow-start")
            lock_acquired.set()
            time.sleep(0.2)
            events.append("uow-end")

    holder = threading.Thread(target=hold_lock_like_a_concurrent_unit_of_work_commit)
    holder.start()
    assert lock_acquired.wait(timeout=5), "background writer never acquired the lock"

    # Runs synchronously on the main thread (the one the fixture's SQLite
    # session belongs to) -- it must block here until the lock above is
    # released, not race it.
    tenant_context_service.set_active_organization(target_org.id)
    events.append("switch-done")
    holder.join(timeout=5)

    assert events == ["uow-start", "uow-end", "switch-done"], (
        "commit_context_switch must not commit while another writer holds the "
        "shared SQLite write lock -- it should wait, not race it"
    )


def test_commit_context_switch_lock_is_a_postgres_no_op() -> None:
    """Production runs on PostgreSQL, which handles concurrent writers
    natively via MVCC -- unlike SQLite, it has no single-writer file lock to
    protect against. `commit_context_switch` reuses `sqlite_write_lock`
    unconditionally, so this must resolve to a genuine no-op for a
    postgres-bound session: it must never serialize two independent
    Postgres commits, or this fix would be a needless throughput regression
    in production."""

    class _FakeDialect:
        def __init__(self, name: str) -> None:
            self.name = name

    class _FakeBind:
        def __init__(self, dialect_name: str) -> None:
            self.dialect = _FakeDialect(dialect_name)

    class _FakeSession:
        def get_bind(self):
            return _FakeBind("postgresql")

    lock_a = sqlite_write_lock(_FakeSession())
    lock_b = sqlite_write_lock(_FakeSession())
    assert lock_a is not _SQLITE_WRITE_LOCK

    events: list[str] = []
    start_barrier = threading.Barrier(2)

    def slow_commit() -> None:
        start_barrier.wait()
        with lock_a:
            events.append("A-start")
            time.sleep(0.2)
            events.append("A-end")

    def concurrent_commit() -> None:
        start_barrier.wait()
        time.sleep(0.05)
        with lock_b:
            events.append("B-start")

    t1 = threading.Thread(target=slow_commit)
    t2 = threading.Thread(target=concurrent_commit)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # B must run WHILE A is still mid-commit -- proof the two Postgres
    # writers were never serialized against each other.
    assert events[:2] == ["A-start", "B-start"], (
        "PostgreSQL commits must never be serialized by this lock"
    )
