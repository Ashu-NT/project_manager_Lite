"""Migration x4y5z6a7b8c9: adds tasks.is_milestone, the single source of
truth replacing the old implicit duration_days<=0 / name-sniffing
milestone detection (see docs/pm_modernization/R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md,
"Milestones")."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def _insert_task(connection, *, task_id: str, project_id: str, duration_days: int) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO tasks (id, project_id, task_code, wbs_code, name, description, "
            "duration_days, status, priority, percent_complete, version) "
            "VALUES (:id, :project_id, :task_code, :wbs_code, :name, '', "
            ":duration_days, 'TODO', 0, 0, 1)"
        ),
        {
            "id": task_id,
            "project_id": project_id,
            "task_code": f"TSK-{task_id}",
            "wbs_code": f"TSK-{task_id}",
            "name": f"Task {task_id}",
            "duration_days": duration_days,
        },
    )


def test_is_milestone_migration_backfills_from_zero_duration(tmp_path) -> None:
    database_path = tmp_path / "milestone.db"
    config = _config(database_path)
    command.upgrade(config, "k3i9kex13spt")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.begin() as connection:
        tenant_id, organization_id = connection.execute(
            sa.text(
                "SELECT tenant_id, id FROM organizations "
                "WHERE tenant_id IS NOT NULL ORDER BY id LIMIT 1"
            )
        ).one()
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, tenant_id, organization_id, name, description, status, version) "
                "VALUES ('proj-1', :tenant_id, :organization_id, 'Repro Project', '', 'active', 1)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        _insert_task(connection, task_id="task-milestone", project_id="proj-1", duration_days=0)
        _insert_task(connection, task_id="task-normal", project_id="proj-1", duration_days=5)

    command.upgrade(config, "x4y5z6a7b8c9")

    with engine.begin() as connection:
        rows = dict(
            connection.execute(sa.text("SELECT id, is_milestone FROM tasks ORDER BY id")).all()
        )
    assert rows["task-milestone"] in (1, True)
    assert rows["task-normal"] in (0, False)

    command.downgrade(config, "k3i9kex13spt")
    with engine.begin() as connection:
        cols = {col["name"] for col in sa.inspect(connection).get_columns("tasks")}
    assert "is_milestone" not in cols
