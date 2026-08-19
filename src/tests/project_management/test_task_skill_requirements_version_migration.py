from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_task_skill_requirements_has_version_column_after_full_migration_chain(tmp_path) -> None:
    """Regression test for a real, shipped migration bug: the original
    i2j3k4l5m6n7_pm_enterprise_upgrade migration's `create_table()` for
    `task_skill_requirements` omitted the `version` column that
    `TaskSkillRequirementORM` (and its sibling tables created in the same
    migration, `resource_skills`/`resource_certifications`, which *did*
    include it) has always declared -- any query selecting the full ORM
    column list failed with
    `sqlite3.OperationalError: no such column: task_skill_requirements.version`
    (surfaced in the Assign Resource dialog's availability/skill check).
    Fixed by a9f3e7c2b8d1_add_task_skill_requirements_version.py.
    """
    database_path = tmp_path / "task-skill-requirements-version.db"
    config = _config(database_path)
    command.upgrade(config, "head")

    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("task_skill_requirements")}
    assert "version" in columns


def test_task_skill_requirements_version_migration_downgrades_cleanly(tmp_path) -> None:
    database_path = tmp_path / "task-skill-requirements-version-downgrade.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    # Explicit target, not the relative "-1" this used to use: "-1" means
    # "one revision before wherever head currently is," which silently
    # downgrades a DIFFERENT migration every time a new one is added on
    # top of this one (as x4y5z6a7b8c9_add_task_is_milestone.py did) --
    # this test must always exercise a9f3e7c2b8d1's own downgrade.
    command.downgrade(config, "q7r8s9t0u1v2")

    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    inspector = sa.inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("task_skill_requirements")}
    assert "version" not in columns

    # Re-upgrading must be idempotent-safe (the _has_column guard), not just
    # a one-shot fix. Re-inspect with a fresh engine/connection rather than
    # reusing the inspector above, which can hold a stale reflected schema
    # from before this second upgrade.
    command.upgrade(config, "head")
    fresh_engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    fresh_inspector = sa.inspect(fresh_engine)
    columns_after = {col["name"] for col in fresh_inspector.get_columns("task_skill_requirements")}
    assert "version" in columns_after
