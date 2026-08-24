from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_task_skill_requirements_has_version_column_after_full_migration_chain(tmp_path) -> None:
    """The fresh baseline must match the current ORM's version contract."""
    database_path = tmp_path / "task-skill-requirements-version.db"
    config = _config(database_path)
    command.upgrade(config, "head")

    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("task_skill_requirements")}
    assert "version" in columns
    engine.dispose()


def test_fresh_baseline_task_skill_requirements_round_trip_is_clean(tmp_path) -> None:
    database_path = tmp_path / "task-skill-requirements-version-downgrade.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)
    assert "task_skill_requirements" not in inspector.get_table_names()
    engine.dispose()

    command.upgrade(config, "head")
    fresh_engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    fresh_inspector = sa.inspect(fresh_engine)
    columns_after = {col["name"] for col in fresh_inspector.get_columns("task_skill_requirements")}
    assert "version" in columns_after
    fresh_engine.dispose()
