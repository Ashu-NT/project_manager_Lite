from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.api.desktop import (
    TaskCreateCommand,
    TaskWbsMoveCommand,
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.infrastructure.importers.tasks.csv.task_csv_importer import (
    import_tasks,
)


def _project(services, name: str):
    return services["project_service"].create_project(name, "")


def test_task_wbs_builds_ordered_hierarchy_and_rolls_up_execution(services) -> None:
    project = _project(services, "WBS Rollup")
    tasks = services["task_service"]
    summary = tasks.create_task(project.id, "Delivery Package", duration_days=10)
    first = tasks.create_task(
        project.id,
        "Foundation Work",
        parent_task_id=summary.id,
        start_date=date(2026, 8, 3),
        duration_days=2,
    )
    second = tasks.create_task(
        project.id,
        "Commissioning Work",
        parent_task_id=summary.id,
        start_date=date(2026, 8, 10),
        duration_days=3,
    )
    tasks.update_progress(first.id, percent_complete=100)
    tasks.update_progress(second.id, percent_complete=50)

    nodes = tasks.list_task_hierarchy(project.id)
    rollup = tasks.get_task_hierarchy_rollup(summary.id)

    assert [(node.task.wbs_code, node.depth, node.is_summary) for node in nodes] == [
        ("1", 0, True),
        ("1.1", 1, False),
        ("1.2", 1, False),
    ]
    assert rollup.descendant_task_ids == (first.id, second.id)
    assert rollup.leaf_task_ids == (first.id, second.id)
    assert rollup.start_date == first.start_date
    assert rollup.end_date == second.end_date
    assert rollup.duration_days == 8
    assert rollup.percent_complete == 70.0
    assert rollup.status == TaskStatus.IN_PROGRESS


def test_task_wbs_move_recodes_subtree_and_prevents_cycles(services) -> None:
    project = _project(services, "WBS Move")
    tasks = services["task_service"]
    source = tasks.create_task(project.id, "Source Package")
    target = tasks.create_task(project.id, "Target Package")
    child = tasks.create_task(project.id, "Child Package", parent_task_id=source.id)
    grandchild = tasks.create_task(project.id, "Execution Leaf", parent_task_id=child.id)

    moved = tasks.move_task(
        child.id,
        parent_task_id=target.id,
        sort_order=0,
        expected_version=child.version,
    )

    assert moved.parent_task_id == target.id
    assert moved.wbs_code == "2.1"
    assert tasks.get_task(grandchild.id).wbs_code == "2.1.1"
    with pytest.raises(BusinessRuleError) as exc:
        tasks.move_task(target.id, parent_task_id=grandchild.id)
    assert exc.value.code == "TASK_WBS_CYCLE"


def test_task_wbs_recode_writes_descendants_before_reusing_their_code(services) -> None:
    project = _project(services, "WBS Recode Ordering")
    tasks = services["task_service"]
    summary = tasks.create_task(project.id, "Recode Package")
    leaf = tasks.create_task(project.id, "Recode Execution", parent_task_id=summary.id)

    recoded = tasks.recode_task(summary.id, "1.1")

    assert recoded.wbs_code == "1.1"
    assert recoded.sort_order == summary.sort_order
    assert tasks.get_task(leaf.id).wbs_code == "1.1.1"


def test_task_wbs_rejects_cross_project_parent_and_summary_execution(services) -> None:
    first_project = _project(services, "WBS Project One")
    second_project = _project(services, "WBS Project Two")
    tasks = services["task_service"]
    summary = tasks.create_task(first_project.id, "Summary Package")
    leaf = tasks.create_task(first_project.id, "Execution Leaf", parent_task_id=summary.id)

    with pytest.raises(BusinessRuleError) as exc:
        tasks.create_task(
            second_project.id,
            "Foreign Child",
            parent_task_id=summary.id,
        )
    assert exc.value.code == "TASK_WBS_PARENT_PROJECT_MISMATCH"

    with pytest.raises(BusinessRuleError) as exc:
        tasks.set_status(summary.id, TaskStatus.IN_PROGRESS)
    assert exc.value.code == "TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"

    with pytest.raises(BusinessRuleError) as exc:
        tasks.add_dependency(
            summary.id,
            leaf.id,
            DependencyType.FINISH_TO_START,
        )
    assert exc.value.code == "TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"

    resource = services["resource_service"].create_resource("WBS Crew", "Planner")
    with pytest.raises(BusinessRuleError) as exc:
        tasks.assign_resource(summary.id, resource.id)
    assert exc.value.code == "TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"

    with pytest.raises(BusinessRuleError) as exc:
        tasks.delete_task(summary.id)
    assert exc.value.code == "TASK_WBS_SUMMARY_NOT_EMPTY"


def test_task_wbs_bulk_mutations_prevalidate_and_delete_children_atomically(services) -> None:
    project = _project(services, "WBS Bulk Mutation")
    tasks = services["task_service"]
    summary = tasks.create_task(project.id, "Bulk Summary")
    leaf = tasks.create_task(project.id, "Bulk Execution", parent_task_id=summary.id)
    surviving_root = tasks.create_task(project.id, "Surviving Root")

    with pytest.raises(BusinessRuleError) as exc:
        tasks.set_tasks_status((leaf.id, summary.id), TaskStatus.DONE)
    assert exc.value.code == "TASK_WBS_SUMMARY_EXECUTION_FORBIDDEN"
    assert tasks.get_task(leaf.id).status == TaskStatus.TODO

    with pytest.raises(BusinessRuleError) as exc:
        tasks.delete_tasks((summary.id,))
    assert exc.value.code == "TASK_WBS_SUMMARY_NOT_EMPTY"
    assert tasks.get_task(summary.id) is not None
    assert tasks.get_task(leaf.id) is not None

    assert tasks.delete_tasks((summary.id, leaf.id)) == (summary.id, leaf.id)
    assert tasks.get_task(summary.id) is None
    assert tasks.get_task(leaf.id) is None
    assert tasks.get_task(surviving_root.id).sort_order == 0


def test_scheduling_runs_only_execution_leaves(services) -> None:
    project = _project(services, "WBS Scheduling")
    tasks = services["task_service"]
    summary = tasks.create_task(
        project.id,
        "Schedule Package",
        start_date=date(2026, 8, 3),
        duration_days=20,
    )
    leaf = tasks.create_task(
        project.id,
        "Schedule Leaf",
        parent_task_id=summary.id,
        start_date=date(2026, 8, 3),
        duration_days=3,
    )

    schedule = services["scheduling_engine"].recalculate_project_schedule(project.id)

    assert set(schedule) == {leaf.id}


def test_desktop_tasks_expose_wbs_summary_rollups_and_move_command(services) -> None:
    project = _project(services, "WBS Desktop")
    api = build_project_management_tasks_desktop_api(
        project_service=services["project_service"],
        task_service=services["task_service"],
    )
    summary = api.create_task(
        TaskCreateCommand(project_id=project.id, name="Desktop Package")
    )
    leaf = api.create_task(
        TaskCreateCommand(
            project_id=project.id,
            name="Desktop Execution",
            parent_task_id=summary.id,
            start_date=date(2026, 8, 4),
            duration_days=2,
        )
    )

    rows = api.list_tasks(project.id)

    assert [(row.wbs_code, row.hierarchy_depth, row.is_summary) for row in rows] == [
        ("1", 0, True),
        ("1.1", 1, False),
    ]
    assert rows[0].duration_days == 2
    moved = api.move_task(
        TaskWbsMoveCommand(
            task_id=leaf.id,
            parent_task_id=None,
            wbs_code="2",
            expected_version=leaf.version,
        )
    )
    assert moved.parent_task_id is None
    assert moved.wbs_code == "2"


def test_task_csv_import_resolves_parent_declared_later(services) -> None:
    project = _project(services, "WBS Import")
    summary = import_tasks(
        [
            (
                2,
                {
                    "project_id": project.id,
                    "name": "Imported Execution",
                    "wbs_code": "1.1",
                    "parent_wbs_code": "1",
                },
            ),
            (
                3,
                {
                    "project_id": project.id,
                    "name": "Imported Package",
                    "wbs_code": "1",
                },
            ),
        ],
        project_service=services["project_service"],
        task_service=services["task_service"],
    )

    nodes = services["task_service"].list_task_hierarchy(project.id)
    assert summary.created_count == 2
    assert summary.error_count == 0
    assert [(node.task.wbs_code, node.depth) for node in nodes] == [
        ("1", 0),
        ("1.1", 1),
    ]
