"""Fresh-baseline contract for explicit task milestone state."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_fresh_baseline_uses_explicit_milestone_state(tmp_path) -> None:
    database_path = tmp_path / "milestone.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO tenants (id, tenant_code, display_name) VALUES "
                "('milestone-tenant', 'MILESTONE-TENANT', 'Milestone Tenant')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO organizations "
                "(id, tenant_id, organization_code, display_name) VALUES "
                "('milestone-org', 'milestone-tenant', 'MILESTONE-ORG', "
                "'Milestone Organization')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(id, tenant_id, organization_id, project_code, name, description, "
                "status, version) VALUES "
                "('milestone-project', 'milestone-tenant', 'milestone-org', "
                "'MILESTONE-PROJECT', 'Milestone Project', '', 'PLANNED', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO tasks "
                "(id, project_id, task_code, wbs_code, name, description, duration_days, "
                "status, priority, percent_complete, version) VALUES "
                "('zero-duration-task', 'milestone-project', 'TASK-ZERO', '1', "
                "'Zero Duration', '', 0, 'TODO', 0, 0, 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO tasks "
                "(id, project_id, task_code, wbs_code, name, description, duration_days, "
                "is_milestone, status, priority, percent_complete, version) VALUES "
                "('explicit-milestone', 'milestone-project', 'TASK-MILESTONE', '2', "
                "'Explicit Milestone', '', 5, 1, 'TODO', 0, 0, 1)"
            )
        )

        rows = dict(
            connection.execute(
                sa.text("SELECT id, is_milestone FROM tasks ORDER BY id")
            ).all()
        )

    assert rows["zero-duration-task"] in (0, False)
    assert rows["explicit-milestone"] in (1, True)
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "tasks" not in sa.inspect(engine).get_table_names()
    engine.dispose()
