from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_fresh_baseline_creates_one_active_scoring_template_per_org_index(tmp_path) -> None:
    database_path = tmp_path / "portfolio-scoring-one-active.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        indexes = {
            row["name"]: row
            for row in inspector.get_indexes("portfolio_scoring_templates")
        }
        template_count = connection.execute(
            sa.text("SELECT COUNT(*) FROM portfolio_scoring_templates")
        ).scalar_one()

    assert "uq_portfolio_scoring_one_active_per_org" in indexes
    assert bool(indexes["uq_portfolio_scoring_one_active_per_org"]["unique"])
    assert indexes["uq_portfolio_scoring_one_active_per_org"]["column_names"] == ["organization_id"]
    assert template_count == 0
    engine.dispose()

    command.downgrade(config, "c3f6a1b8d9e0")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.connect() as connection:
        indexes_after_downgrade = {
            row["name"] for row in sa.inspect(connection).get_indexes("portfolio_scoring_templates")
        }
    assert "uq_portfolio_scoring_one_active_per_org" not in indexes_after_downgrade
    engine.dispose()


def test_migration_normalizes_pre_existing_duplicate_active_rows_deterministically(tmp_path) -> None:
    database_path = tmp_path / "portfolio-scoring-one-active-dirty.db"
    config = _config(database_path)
    command.upgrade(config, "c3f6a1b8d9e0")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """
                INSERT INTO portfolio_scoring_templates
                    (id, tenant_id, organization_id, name, summary, strategic_weight,
                     value_weight, urgency_weight, risk_weight, is_active,
                     created_at, updated_at)
                VALUES
                    ('tpl-older', NULL, 'org-dirty', 'Older Active', '', 3, 2, 2, 1, 1,
                     '2026-01-01T00:00:00', '2026-01-01T00:00:00'),
                    ('tpl-newer', NULL, 'org-dirty', 'Newer Active', '', 3, 2, 2, 1, 1,
                     '2026-01-02T00:00:00', '2026-01-02T00:00:00')
                """
            )
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT id, is_active FROM portfolio_scoring_templates WHERE organization_id = 'org-dirty'"
            )
        ).all()
    engine.dispose()

    active_ids = [row.id for row in rows if row.is_active]
    assert active_ids == ["tpl-newer"], (
        "deterministic normalization keeps the most-recently-updated row active per organization"
    )
