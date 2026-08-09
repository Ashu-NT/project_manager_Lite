from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_financial_period_migration_is_reversible_and_enforces_catalog_identity(tmp_path) -> None:
    database_path = tmp_path / "financial-periods.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    inspector = sa.inspect(engine)
    assert "financial_periods" in inspector.get_table_names()
    unique_sets = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("financial_periods")
    }
    assert ("tenant_id", "organization_id", "code") in unique_sets
    assert (
        "tenant_id",
        "organization_id",
        "fiscal_year",
        "period_number",
    ) in unique_sets
    engine.dispose()

    command.downgrade(config, "n1o2p3q4r5s6")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "financial_periods" not in sa.inspect(engine).get_table_names()
    engine.dispose()
