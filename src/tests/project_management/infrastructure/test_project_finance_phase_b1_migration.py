from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_fresh_baseline_creates_finance_profile_schema_without_manufactured_rows(
    tmp_path,
) -> None:
    database_path = tmp_path / "phase-b1-finance.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        tables = set(inspector.get_table_names())
        profile_columns = {
            column["name"] for column in inspector.get_columns("project_finance_profiles")
        }
        profile_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM project_finance_profiles")
        ).scalar_one()

    assert {
        "project_finance_profiles",
        "project_finance_cost_codes",
        "project_finance_cost_code_restrictions",
    }.issubset(tables)
    assert {
        "tenant_id",
        "organization_id",
        "project_id",
        "currency_code",
        "budget_control_mode",
        "version",
    }.issubset(profile_columns)
    assert profile_count == 0
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_finance_profiles" not in sa.inspect(engine).get_table_names()
    engine.dispose()
