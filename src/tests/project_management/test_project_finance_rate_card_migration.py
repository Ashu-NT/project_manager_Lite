from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_rate_card_migration_backfills_legacy_card_at_fixed_historical_epoch(tmp_path) -> None:
    # The regression this migration test exists for: Resource.hourly_rate was,
    # before this cutover, read with no date-scoping at all — applicable to
    # ANY historical date. Backfilling the legacy rate line with the
    # migration's own run date (rather than a fixed historical epoch) would
    # make every report `as_of` before that date suddenly find "no applicable
    # rate" where today it reads the resource's hourly rate successfully.
    database_path = tmp_path / "rate-card-migration.db"
    config = _config(database_path)
    command.upgrade(config, "k9l0m1n2o3p4")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.begin() as connection:
        tenant_id, organization_id = connection.execute(
            sa.text(
                "SELECT o.tenant_id, o.id FROM organizations o "
                "WHERE o.tenant_id IS NOT NULL ORDER BY o.id LIMIT 1"
            )
        ).one()
        connection.execute(
            sa.text(
                "INSERT INTO resources "
                "(id, tenant_id, resource_code, name, role, hourly_rate, is_active, "
                "capacity_percent, cost_type, currency_code, worker_type, organization_id, "
                "version) "
                "VALUES ('migration-resource', :tenant_id, 'MIG-RES', 'Migration Resource', "
                "'Engineer', 50.0, 1, 100.0, 'LABOR', 'USD', 'EXTERNAL', :organization_id, 1)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
    engine.dispose()

    command.upgrade(config, "l0m1n2o3p4q5")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.connect() as connection:
        card = connection.execute(
            sa.text(
                "SELECT id, card_kind FROM project_finance_rate_cards "
                "WHERE organization_id = :organization_id"
            ),
            {"organization_id": organization_id},
        ).one()
        line = connection.execute(
            sa.text(
                "SELECT rate_amount, rate_currency, effective_from, effective_to, origin "
                "FROM project_finance_rate_card_lines WHERE resource_id = 'migration-resource'"
            )
        ).one()
    engine.dispose()

    assert card.card_kind == "legacy"
    assert float(line.rate_amount) == 50.0
    assert line.rate_currency == "USD"
    assert line.origin == "legacy_seeded"
    assert line.effective_to is None
    assert date.fromisoformat(line.effective_from) == date(1970, 1, 1)

    command.downgrade(config, "k9l0m1n2o3p4")
