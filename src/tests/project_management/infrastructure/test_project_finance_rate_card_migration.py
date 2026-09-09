from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_fresh_baseline_creates_effective_dated_rate_card_schema_without_legacy_rows(
    tmp_path,
) -> None:
    database_path = tmp_path / "rate-card-migration.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        tables = set(inspector.get_table_names())
        line_columns = {
            column["name"]
            for column in inspector.get_columns("project_finance_rate_card_lines")
        }
        card_columns = {
            column["name"]
            for column in inspector.get_columns("project_finance_rate_cards")
        }
        line_checks = {
            check["name"]: check["sqltext"]
            for check in inspector.get_check_constraints(
                "project_finance_rate_card_lines"
            )
        }
        card_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM project_finance_rate_cards")
        ).scalar_one()
        line_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM project_finance_rate_card_lines")
        ).scalar_one()

    assert {
        "project_finance_rate_cards",
        "project_finance_rate_card_lines",
    }.issubset(tables)
    assert {
        "tenant_id",
        "organization_id",
        "rate_card_id",
        "effective_from",
        "effective_to",
        "rate_amount",
        "rate_currency",
        "origin",
    }.issubset(line_columns)
    assert "card_kind" not in card_columns
    assert "legacy_seeded" not in str(line_checks)
    assert "origin = 'configured'" in line_checks["ck_pf_rate_card_lines_origin"]
    assert card_count == 0
    assert line_count == 0
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_finance_rate_cards" not in sa.inspect(engine).get_table_names()
    engine.dispose()
