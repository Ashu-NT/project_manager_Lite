from __future__ import annotations

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError


def _config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def _insert_task(connection, *, task_id: str, project_id: str, name: str, start_date: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO tasks "
            "(id, project_id, task_code, name, description, start_date, status, "
            "priority, percent_complete, version) "
            "VALUES (:id, :project_id, :task_code, :name, '', :start_date, "
            "'TODO', 0, 0, 1)"
        ),
        {
            "id": task_id,
            "project_id": project_id,
            "task_code": f"TSK-{task_id}",
            "name": name,
            "start_date": start_date,
        },
    )


def test_task_wbs_migration_backfills_roots_and_enforces_same_project_parent(tmp_path) -> None:
    database_path = tmp_path / "task-wbs.db"
    config = _config(database_path)
    command.upgrade(config, "j8k9l0m1n2o3")
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
                "INSERT INTO projects "
                "(id, tenant_id, organization_id, project_code, name, description, "
                "status, currency, version) VALUES "
                "('wbs-project-a', :tenant_id, :organization_id, 'WBS-A', "
                "'WBS A', '', 'PLANNED', 'EUR', 1), "
                "('wbs-project-b', :tenant_id, :organization_id, 'WBS-B', "
                "'WBS B', '', 'PLANNED', 'EUR', 1)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        _insert_task(
            connection,
            task_id="late-task",
            project_id="wbs-project-a",
            name="Late",
            start_date="2026-08-10",
        )
        _insert_task(
            connection,
            task_id="early-task",
            project_id="wbs-project-a",
            name="Early",
            start_date="2026-08-03",
        )
        _insert_task(
            connection,
            task_id="foreign-task",
            project_id="wbs-project-b",
            name="Foreign",
            start_date="2026-08-04",
        )
    engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        rows = connection.execute(
            sa.text(
                "SELECT id, parent_task_id, wbs_code, sort_order FROM tasks "
                "WHERE project_id = 'wbs-project-a' ORDER BY sort_order"
            )
        ).all()
        assert rows == [
            ("early-task", None, "1", 0),
            ("late-task", None, "2", 1),
        ]
        connection.execute(
            sa.text(
                "UPDATE tasks SET parent_task_id = 'early-task' "
                "WHERE id = 'late-task'"
            )
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    "UPDATE tasks SET parent_task_id = 'foreign-task' "
                    "WHERE id = 'late-task'"
                )
            )
    engine.dispose()

    command.downgrade(config, "j8k9l0m1n2o3")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    columns = {column["name"] for column in sa.inspect(engine).get_columns("tasks")}
    assert {"parent_task_id", "wbs_code", "sort_order"}.isdisjoint(columns)
    engine.dispose()
