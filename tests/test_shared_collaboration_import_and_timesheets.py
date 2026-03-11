from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from core.exceptions import ValidationError


def test_db_backed_collaboration_store_persists_and_marks_mentions(services):
    ps = services["project_service"]
    ts = services["task_service"]
    store = services["task_collaboration_store"]

    project = ps.create_project("Collaboration DB")
    task = ts.create_task(project.id, "Commented Task", start_date=date(2026, 3, 1), duration_days=2)

    store.add_comment(
        task_id=task.id,
        author="alice",
        body="Please review this @bob and @robert",
        attachments=[],
    )

    rows = store.list_comments(task.id)
    assert len(rows) == 1
    assert rows[0]["author"] == "alice"
    assert rows[0]["mentions"] == ["bob", "robert"]
    assert store.unread_mentions_count_for_users(["bob", "robert"]) == 1

    store.mark_task_mentions_read(task_id=task.id, username="bob")
    assert store.unread_mentions_count_for_users(["bob", "robert"]) == 0


def test_time_entries_roll_up_assignment_hours_and_replace_aggregate_edit(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Timesheet Project")
    task = ts.create_task(project.id, "Timesheet Task", start_date=date(2026, 3, 2), duration_days=3)
    resource = rs.create_resource("Time Logger", hourly_rate=110.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=50.0)

    first = ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 3, 2),
        hours=2.5,
        note="Design review",
    )
    second = ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 3, 3),
        hours=3.0,
        note="Implementation",
    )

    assert len(ts.list_time_entries_for_assignment(assignment.id)) == 2
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(5.5)

    ts.update_time_entry(first.id, hours=3.0, note="Design workshop")
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(6.0)

    ts.delete_time_entry(second.id)
    remaining = ts.list_time_entries_for_assignment(assignment.id)
    assert len(remaining) == 1
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(3.0)

    with pytest.raises(ValidationError, match="timesheet"):
        ts.set_assignment_hours(assignment.id, 10.0)


def test_data_import_service_imports_projects_resources_tasks_and_costs(services):
    importer = services["data_import_service"]
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cs = services["cost_service"]

    root = Path(__file__).resolve().parents[1]
    tmp = root / "pytest_import_workspace" / uuid4().hex
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        (tmp / "projects.csv").write_text(
            "\n".join(
                [
                    "name,description,currency,start_date,end_date,status,planned_budget",
                    "Import Alpha,Initial import,USD,2026-04-01,2026-04-30,ACTIVE,5000",
                ]
            ),
            encoding="utf-8",
        )
        project_summary = importer.import_csv("projects", tmp / "projects.csv")
        assert project_summary.created_count == 1
        project = next(item for item in ps.list_projects() if item.name == "Import Alpha")
        assert project.currency == "USD"

        (tmp / "resources.csv").write_text(
            "\n".join(
                [
                    "name,role,hourly_rate,currency_code,capacity_percent",
                    "Import Dev,Developer,125,USD,80",
                ]
            ),
            encoding="utf-8",
        )
        resource_summary = importer.import_csv("resources", tmp / "resources.csv")
        assert resource_summary.created_count == 1
        resource = next(item for item in rs.list_resources() if item.name == "Import Dev")
        assert resource.capacity_percent == pytest.approx(80.0)

        (tmp / "tasks.csv").write_text(
            "\n".join(
                [
                    "project_name,name,description,start_date,duration_days,status,priority,percent_complete",
                    "Import Alpha,Imported Task,Imported from CSV,2026-04-02,4,IN_PROGRESS,2,25",
                ]
            ),
            encoding="utf-8",
        )
        task_summary = importer.import_csv("tasks", tmp / "tasks.csv")
        assert task_summary.created_count == 1
        task = next(item for item in ts.list_tasks_for_project(project.id) if item.name == "Imported Task")
        assert task.percent_complete == pytest.approx(25.0)

        (tmp / "costs.csv").write_text(
            "\n".join(
                [
                    "project_name,task_name,description,planned_amount,actual_amount,currency_code,cost_type",
                    "Import Alpha,Imported Task,Imported Cost,1200,300,USD,LABOR",
                ]
            ),
            encoding="utf-8",
        )
        cost_summary = importer.import_csv("costs", tmp / "costs.csv")
        assert cost_summary.created_count == 1
        costs = cs.list_cost_items_for_project(project.id)
        assert len(costs) == 1
        assert costs[0].task_id == task.id
        assert costs[0].actual_amount == pytest.approx(300.0)

        (tmp / "projects_update.csv").write_text(
            "\n".join(
                [
                    "name,description,currency,start_date,end_date,status,planned_budget",
                    "Import Alpha,Updated import,EUR,2026-04-01,2026-05-02,ACTIVE,7500",
                ]
            ),
            encoding="utf-8",
        )
        update_summary = importer.import_csv("projects", tmp / "projects_update.csv")
        assert update_summary.updated_count == 1
        updated_project = next(item for item in ps.list_projects() if item.name == "Import Alpha")
        assert updated_project.description == "Updated import"
        assert updated_project.currency == "EUR"
        assert updated_project.planned_budget == pytest.approx(7500.0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
