from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_head_of_department_migration_preserves_existing_assignments(tmp_path) -> None:
    database_path = tmp_path / "hod-migration.db"
    config = _config(database_path)
    command.upgrade(config, "c7f2a5d91b48")

    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        departments = sa.Table("departments", sa.MetaData(), autoload_with=engine)
        conn.execute(
            departments.insert().values(
                id="dep-1",
                tenant_id=None,
                organization_id="org-1",
                department_code="ENG",
                name="Engineering",
                description=None,
                site_id=None,
                parent_department_id=None,
                department_type=None,
                cost_center_code=None,
                manager_employee_id="emp-1",
                is_active=True,
                created_at=now,
                updated_at=now,
                notes=None,
                version=1,
            )
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    columns = {col["name"] for col in sa.inspect(engine).get_columns("departments")}
    assert "head_of_department_employee_id" in columns
    assert "manager_employee_id" not in columns

    with engine.connect() as conn:
        departments = sa.Table("departments", sa.MetaData(), autoload_with=engine)
        preserved = conn.execute(
            sa.select(departments.c.head_of_department_employee_id).where(departments.c.id == "dep-1")
        ).scalar_one()
    assert preserved == "emp-1"
    engine.dispose()

    command.downgrade(config, "c7f2a5d91b48")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    columns = {col["name"] for col in sa.inspect(engine).get_columns("departments")}
    assert "manager_employee_id" in columns
    assert "head_of_department_employee_id" not in columns

    with engine.connect() as conn:
        departments = sa.Table("departments", sa.MetaData(), autoload_with=engine)
        restored = conn.execute(
            sa.select(departments.c.manager_employee_id).where(departments.c.id == "dep-1")
        ).scalar_one()
    assert restored == "emp-1"
    engine.dispose()
