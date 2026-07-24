from __future__ import annotations

from importlib import import_module

import pytest
import sqlalchemy as sa


_MIGRATION_MODULES = (
    "src.infra.persistence.migrations.versions.u6v7w8x9y0z1_backfill_audit_logs_to_activity",
    "src.infra.persistence.migrations.versions.v7w8x9y0z1a2_backfill_audit_logs_security_to_audit",
)


class _FakeInspector:
    def get_table_names(self):
        return ["audit_logs"]


class _EmptyResult:
    def fetchall(self):
        return []


class _CheckpointConn:
    def __init__(self, checkpoint_exc: sa.exc.OperationalError | None = None) -> None:
        self._checkpoint_exc = checkpoint_exc
        self.statements: list[str] = []

    def execute(self, statement, params=None):
        del params
        sql_text = str(statement)
        self.statements.append(sql_text)
        if "PRAGMA wal_checkpoint" in sql_text:
            if self._checkpoint_exc is not None:
                raise self._checkpoint_exc
            return _EmptyResult()
        return _EmptyResult()


@pytest.mark.parametrize("module_name", _MIGRATION_MODULES)
def test_backfill_migrations_ignore_sqlite_lock_during_wal_checkpoint(
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module(module_name)
    conn = _CheckpointConn(
        sa.exc.OperationalError(
            "PRAGMA wal_checkpoint",
            None,
            RuntimeError("database table is locked"),
        )
    )
    monkeypatch.setattr(module, "op", type("Op", (), {"get_bind": staticmethod(lambda: conn)})())
    monkeypatch.setattr(module.sa, "inspect", lambda _: _FakeInspector())

    module.upgrade()

    assert any("PRAGMA wal_checkpoint" in text for text in conn.statements)


@pytest.mark.parametrize("module_name", _MIGRATION_MODULES)
def test_backfill_migrations_still_raise_non_lock_checkpoint_errors(
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module(module_name)
    conn = _CheckpointConn(
        sa.exc.OperationalError(
            "PRAGMA wal_checkpoint",
            None,
            RuntimeError("disk I/O error"),
        )
    )
    monkeypatch.setattr(module, "op", type("Op", (), {"get_bind": staticmethod(lambda: conn)})())
    monkeypatch.setattr(module.sa, "inspect", lambda _: _FakeInspector())

    with pytest.raises(sa.exc.OperationalError):
        module.upgrade()
