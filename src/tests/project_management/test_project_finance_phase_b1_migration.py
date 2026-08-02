from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_phase_b1_migration_backfills_profile_and_is_reversible(tmp_path) -> None:
    database_path = tmp_path / "phase-b1-finance.db"
    config = _config(database_path)
    command.upgrade(config, "i7j8k9l0m1n2")
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
                "INSERT INTO projects "
                "(id, tenant_id, project_code, name, description, status, currency, "
                "organization_id, version) "
                "VALUES ('migration-project', :tenant_id, 'MIG-PROJECT', "
                "'Migration Project', '', 'PLANNED', NULL, :organization_id, 1)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(id, tenant_id, project_code, name, description, status, currency, "
                "organization_id, version) "
                "VALUES ('invalid-currency-project', :tenant_id, 'MIG-INVALID', "
                "'Invalid Currency Project', '', 'PLANNED', 'ZZZ', :organization_id, 1)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.connect() as connection:
        profile = connection.execute(
            sa.text(
                "SELECT currency_code, status, version "
                "FROM project_finance_profiles WHERE project_id = 'migration-project'"
            )
        ).one()
        tables = set(sa.inspect(connection).get_table_names())
        fallback_currency = connection.execute(
            sa.text(
                "SELECT currency_code FROM project_finance_profiles "
                "WHERE project_id = 'invalid-currency-project'"
            )
        ).scalar_one()

    assert profile.currency_code == "EUR"
    assert profile.status == "active"
    assert profile.version == 1
    assert fallback_currency == "EUR"
    assert {
        "project_finance_profiles",
        "project_finance_cost_codes",
        "project_finance_cost_code_restrictions",
    }.issubset(tables)
    engine.dispose()

    command.downgrade(config, "i7j8k9l0m1n2")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "project_finance_profiles" not in sa.inspect(engine).get_table_names()
    engine.dispose()
