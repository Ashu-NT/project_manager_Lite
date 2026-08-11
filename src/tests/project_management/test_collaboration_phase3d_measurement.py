"""Phase 3D measurements for Collaboration cross-project reads."""

from __future__ import annotations

import time

import pytest

from src.tests.project_management._sql_measurement_helpers import (
    count_calls,
    measure_sql,
)


_SIZES = {"small": 1, "medium": 5, "large": 12}


def _seed_collaboration_workspace(services, *, project_count: int) -> None:
    projects = services["project_service"]
    tasks = services["task_service"]
    collaboration = services["collaboration_service"]
    for index in range(project_count):
        project = projects.create_project(f"Phase 3D Project {index}")
        task = tasks.create_task(project.id, f"Phase 3D Task {index}")
        collaboration.post_comment(
            task_id=task.id,
            body=f"Phase 3D update {index} for @admin",
        )
        collaboration.touch_task_presence(task.id, activity="reviewing")


@pytest.mark.parametrize("size_name", ["small", "medium", "large"])
def test_phase3d_measure_collaboration_reads(services, size_name, capsys) -> None:
    project_count = _SIZES[size_name]
    _seed_collaboration_workspace(services, project_count=project_count)
    collaboration = services["collaboration_service"]
    targets = [
        (
            collaboration,
            "_read_cross_project_collaboration_facts",
            "collaboration.read_fact_graph",
        ),
        (collaboration._workspace_reader, "read_facts", "collaboration_reader.read_facts"),
        (collaboration._project_repo, "list", "project_repo.list"),
        (collaboration._project_repo, "get", "project_repo.get"),
        (collaboration._task_repo, "list_by_project", "task_repo.list_by_project"),
        (collaboration._comment_repo, "list_recent_for_tasks", "comment_repo.list_recent_for_tasks"),
        (collaboration._presence_repo, "list_recent_for_tasks", "presence_repo.list_recent_for_tasks"),
        (collaboration._audit_repo, "list_recent_for_organization", "audit_repo.list_recent_for_organization"),
        (collaboration._user_session, "has_project_permission", "session.has_project_permission"),
    ]
    operations = (
        ("inbox", collaboration.list_inbox),
        ("workspace", collaboration.list_workspace_snapshot),
    )

    for operation_name, operation in operations:
        with measure_sql(services["session"]) as sql_stats, count_calls(targets) as calls:
            started = time.perf_counter()
            result = operation(limit=200)
            wall_time = time.perf_counter() - started
        report = "\n".join(
            (
                f"\n=== Phase 3D post-cutover [{size_name}:{operation_name}] ===",
                f"projects={project_count}",
                f"wall_time_s={wall_time:.6f}",
                f"db_time_s={sql_stats.total_db_time_s:.6f}",
                f"sql_total_statements={sql_stats.total_statements}",
                f"sql_by_table={dict(sql_stats.by_table)}",
                f"call_counts={dict(calls)}",
            )
        )
        print(report)
        with capsys.disabled():
            print(report)

        assert result is not None
        expected_sql = 3 if operation_name == "inbox" else 6
        assert sql_stats.total_statements == expected_sql
        assert calls["collaboration.read_fact_graph"] == 1
        assert calls["collaboration_reader.read_facts"] == 1
        assert calls["project_repo.list"] == 1
        assert calls["project_repo.get"] == 0
        assert calls["task_repo.list_by_project"] == 0
        assert calls["comment_repo.list_recent_for_tasks"] == 0
        assert calls["presence_repo.list_recent_for_tasks"] == 0
        assert calls["session.has_project_permission"] == 0
        assert calls["audit_repo.list_recent_for_organization"] == (
            1 if operation_name == "workspace" else 0
        )
