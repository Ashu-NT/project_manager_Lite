"""Fresh-schema contract for immutable baseline milestone identity."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def test_fresh_baseline_preserves_explicit_baseline_milestone_state(tmp_path) -> None:
    database_path = tmp_path / "baseline-milestone.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO tenants (id, tenant_code, display_name) VALUES "
                "('tenant-1', 'TENANT-1', 'Tenant 1')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO organizations "
                "(id, tenant_id, organization_code, display_name) VALUES "
                "('org-1', 'tenant-1', 'ORG-1', 'Organization 1')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(id, tenant_id, organization_id, project_code, name, description, "
                "status, version) VALUES "
                "('project-1', 'tenant-1', 'org-1', 'PROJECT-1', "
                "'Project 1', '', 'PLANNED', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO project_baselines "
                "(id, project_id, name, created_at, status, version) VALUES "
                "('baseline-1', 'project-1', 'Baseline 1', "
                "'2026-01-01 00:00:00', 'draft', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO baseline_tasks "
                "(id, baseline_id, task_id, task_name, baseline_duration_days, "
                "baseline_planned_cost) VALUES "
                "('snapshot-default', 'baseline-1', 'task-1', 'Task 1', 0, 0)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO baseline_tasks "
                "(id, baseline_id, task_id, task_name, baseline_duration_days, "
                "baseline_is_milestone, baseline_planned_cost) VALUES "
                "('snapshot-milestone', 'baseline-1', 'task-2', 'Task 2', 0, 1, 0)"
            )
        )
        rows = dict(
            connection.execute(
                sa.text(
                    "SELECT id, baseline_is_milestone FROM baseline_tasks ORDER BY id"
                )
            ).all()
        )
        columns = {
            column["name"]
            for column in sa.inspect(connection).get_columns("baseline_tasks")
        }

    assert "baseline_is_milestone" in columns
    assert rows["snapshot-default"] in (0, False)
    assert rows["snapshot-milestone"] in (1, True)
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "baseline_tasks" not in sa.inspect(engine).get_table_names()
    engine.dispose()
