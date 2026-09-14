from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_fresh_schema_uses_active_only_billing_source_uniqueness(tmp_path) -> None:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    database_path = tmp_path / "billing-source-locks.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    try:
        indexes = {
            item["name"]: item
            for item in sa.inspect(engine).get_indexes("project_billing_source_locks")
        }
        active = indexes["uq_billing_locks_active_source"]
        assert active["unique"]
        assert active["column_names"] == [
            "tenant_id", "organization_id", "source_type", "source_id"
        ]
        assert "released" in str(active["dialect_options"]["sqlite_where"])
        assert "uq_billing_locks_source" not in {
            item["name"]
            for item in sa.inspect(engine).get_unique_constraints(
                "project_billing_source_locks"
            )
        }
        corrections = {
            item["name"]: item
            for item in sa.inspect(engine).get_indexes("project_billing_preparations")
        }
        assert corrections["uq_billing_preparations_active_correction"]["unique"]
        predicate = str(
            corrections["uq_billing_preparations_active_correction"][
                "dialect_options"
            ]["sqlite_where"]
        )
        assert "rejected" in predicate and "cancelled" in predicate
    finally:
        engine.dispose()
