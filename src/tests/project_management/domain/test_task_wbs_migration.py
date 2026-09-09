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


def _insert_task(
    connection,
    *,
    task_id: str,
    project_id: str,
    wbs_code: str,
    sort_order: int,
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO tasks "
            "(id, project_id, task_code, wbs_code, sort_order, name, description, "
            "status, priority, percent_complete, version) "
            "VALUES (:id, :project_id, :task_code, :wbs_code, :sort_order, "
            ":name, '', 'TODO', 0, 0, 1)"
        ),
        {
            "id": task_id,
            "project_id": project_id,
            "task_code": f"TSK-{task_id}",
            "wbs_code": wbs_code,
            "sort_order": sort_order,
            "name": f"Task {task_id}",
        },
    )


def test_fresh_baseline_wbs_schema_enforces_same_project_parent(tmp_path) -> None:
    database_path = tmp_path / "task-wbs.db"
    config = _config(database_path)
    command.upgrade(config, "head")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)

    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.execute(
            sa.text(
                "INSERT INTO tenants (id, tenant_code, display_name) VALUES "
                "('wbs-tenant', 'WBS-TENANT', 'WBS Tenant')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO organizations "
                "(id, tenant_id, organization_code, display_name) VALUES "
                "('wbs-org', 'wbs-tenant', 'WBS-ORG', 'WBS Organization')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(id, tenant_id, organization_id, project_code, name, description, "
                "status, version) VALUES "
                "('wbs-project-a', 'wbs-tenant', 'wbs-org', 'WBS-A', "
                "'WBS A', '', 'PLANNED', 1), "
                "('wbs-project-b', 'wbs-tenant', 'wbs-org', 'WBS-B', "
                "'WBS B', '', 'PLANNED', 1)"
            )
        )
        _insert_task(
            connection,
            task_id="parent-task",
            project_id="wbs-project-a",
            wbs_code="1",
            sort_order=0,
        )
        _insert_task(
            connection,
            task_id="child-task",
            project_id="wbs-project-a",
            wbs_code="1.1",
            sort_order=1,
        )
        _insert_task(
            connection,
            task_id="foreign-task",
            project_id="wbs-project-b",
            wbs_code="1",
            sort_order=0,
        )
        connection.commit()

        connection.execute(
            sa.text(
                "UPDATE tasks SET parent_task_id = 'parent-task' "
                "WHERE id = 'child-task'"
            )
        )
        connection.commit()

        with pytest.raises(IntegrityError):
            connection.execute(
                sa.text(
                    "UPDATE tasks SET parent_task_id = 'foreign-task' "
                    "WHERE id = 'child-task'"
                )
            )
        connection.rollback()

        parent_task_id = connection.execute(
            sa.text("SELECT parent_task_id FROM tasks WHERE id = 'child-task'")
        ).scalar_one()
        columns = {column["name"] for column in sa.inspect(connection).get_columns("tasks")}

    assert parent_task_id == "parent-task"
    assert {"parent_task_id", "wbs_code", "sort_order"}.issubset(columns)
    engine.dispose()

    command.downgrade(config, "base")
    engine = sa.create_engine(config.get_main_option("sqlalchemy.url"), future=True)
    assert "tasks" not in sa.inspect(engine).get_table_names()
    engine.dispose()
