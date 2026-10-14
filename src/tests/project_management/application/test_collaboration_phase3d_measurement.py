"""Measurements for purpose-specific Collaboration cross-project reads."""

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
    for index in range(project_count):
        project = projects.create_project(f"Phase 3D Project {index}")
        task = tasks.create_task(project.id, f"Phase 3D Task {index}")
        services["collaboration_comment_commands"].post_comment(
            task_id=task.id,
            body=f"Phase 3D update {index} for @admin",
        )
        services["collaboration_presence_commands"].touch_task_presence(task.id, activity="reviewing")


@pytest.mark.parametrize("size_name", ["small", "medium", "large"])
def test_phase3d_measure_collaboration_reads(services, size_name, capsys) -> None:
    project_count = _SIZES[size_name]
    _seed_collaboration_workspace(services, project_count=project_count)
    visibility_policy = services["collaboration_inbox_query"]._policy
    targets = [
        (
            services["collaboration_comment_query"]._workspace_reader,
            "read_comment_page",
            "collaboration_reader.read_comment_page",
        ),
        (
            services["collaboration_comment_query"]._workspace_reader,
            "read_active_presence",
            "collaboration_reader.read_active_presence",
        ),
        (visibility_policy._project_repo, "list", "project_repo.list"),
        (visibility_policy._project_repo, "get", "project_repo.get"),
        (visibility_policy._task_repo, "list_by_project", "task_repo.list_by_project"),
        (
            services["collaboration_comment_commands"]._comment_repo,
            "list_recent_for_tasks",
            "comment_repo.list_recent_for_tasks",
        ),
        (
            services["collaboration_presence_query"]._presence_repo,
            "list_recent_for_tasks",
            "presence_repo.list_recent_for_tasks",
        ),
        (
            visibility_policy._user_session,
            "has_project_permission",
            "session.has_project_permission",
        ),
    ]
    operations = (
        ("inbox", lambda: services["collaboration_inbox_query"].query_inbox_page(page=1, page_size=200)),
        ("activity", lambda: services["collaboration_inbox_query"].list_recent_activity(limit=100)),
        ("presence", services["collaboration_presence_query"].list_active_presence),
    )

    for operation_name, operation in operations:
        with measure_sql(services["session"]) as sql_stats, count_calls(targets) as calls:
            started = time.perf_counter()
            result = operation()
            wall_time = time.perf_counter() - started
        report = "\n".join(
            (
                f"\n=== Collaboration purpose query [{size_name}:{operation_name}] ===",
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
        assert sql_stats.total_statements <= 6
        assert calls["project_repo.list"] == 1
        assert calls["project_repo.get"] == 0
        assert calls["task_repo.list_by_project"] == 0
        assert calls["comment_repo.list_recent_for_tasks"] == 0
        assert calls["presence_repo.list_recent_for_tasks"] == 0
        assert calls["session.has_project_permission"] == 0
        assert calls["collaboration_reader.read_comment_page"] == (
            0 if operation_name == "presence" else 1
        )
        assert calls["collaboration_reader.read_active_presence"] == (
            1 if operation_name == "presence" else 0
        )
