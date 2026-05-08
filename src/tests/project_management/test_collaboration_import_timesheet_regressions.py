from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.modules.project_management.infrastructure.collaboration_store import TaskCollaborationStore
from src.core.platform.infrastructure.persistence.orm.time import TimeEntryORM
from tests.temp_dirs import cleanup_test_workspace, create_test_workspace


@pytest.fixture
def workspace_dir():
    root = create_test_workspace("regression")
    try:
        yield root
    finally:
        cleanup_test_workspace(root)


def _write_csv(workspace_dir: Path, name: str, lines: list[str]) -> Path:
    path = workspace_dir / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _time_entry_count(services) -> int:
    return services["session"].query(TimeEntryORM).count()


def test_db_collaboration_store_copies_file_attachments_and_preserves_tokens(
    services,
    workspace_dir,
    monkeypatch,
):
    ps = services["project_service"]
    ts = services["task_service"]
    store = services["task_collaboration_store"]
    monkeypatch.setattr("src.core.modules.project_management.infrastructure.collaboration_attachments.user_data_dir", lambda: workspace_dir)

    project = ps.create_project("Collab Attachments")
    task = ts.create_task(project.id, "DB Comment Task", start_date=date(2026, 3, 1), duration_days=1)
    source_dir = workspace_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_file = source_dir / "evidence.txt"
    source_file.write_text("proof", encoding="utf-8")

    row = store.add_comment(
        task_id=task.id,
        author="alice",
        body="Please check this @bob",
        attachments=[str(source_file), "ticket-123"],
    )

    stored_file = Path(row["attachments"][0])
    assert stored_file.exists()
    assert stored_file.read_text(encoding="utf-8") == "proof"
    assert stored_file != source_file
    assert row["attachments"][1] == "ticket-123"

    rows = store.list_comments(task.id)
    assert rows[0]["mentions"] == ["bob"]
    assert rows[0]["attachments"] == row["attachments"]


def test_db_collaboration_store_marks_only_the_selected_task_mentions_as_read(services):
    ps = services["project_service"]
    ts = services["task_service"]
    store = services["task_collaboration_store"]

    project = ps.create_project("Collab Read Scope")
    first_task = ts.create_task(project.id, "Task A", start_date=date(2026, 3, 1), duration_days=1)
    second_task = ts.create_task(project.id, "Task B", start_date=date(2026, 3, 2), duration_days=1)

    store.add_comment(task_id=first_task.id, author="alice", body="Review this @bob", attachments=[])
    store.add_comment(task_id=second_task.id, author="alice", body="Review that @bob", attachments=[])

    store.mark_task_mentions_read(task_id=first_task.id, username="bob")

    assert store.unread_mentions_count_for_users(["bob"]) == 1
    assert store.list_comments(first_task.id)[0]["read_by"] == ["bob"]
    assert store.list_comments(second_task.id)[0]["read_by"] == []


@pytest.mark.parametrize("mode", ["file", "db"])
def test_collaboration_store_rejects_blank_comments(services, workspace_dir, mode):
    if mode == "file":
        store = TaskCollaborationStore(storage_path=workspace_dir / "comments.json")
    else:
        store = services["task_collaboration_store"]

    with pytest.raises(ValueError, match="Comment text is required"):
        store.add_comment(task_id="task-1", author="alice", body="   ", attachments=[])


def test_import_projects_collects_row_errors_without_stopping(services, workspace_dir):
    importer = services["data_import_service"]
    ps = services["project_service"]

    csv_path = _write_csv(
        workspace_dir,
        "projects.csv",
        [
            "name,description,currency,start_date,end_date,status,planned_budget",
            "Good Project,Imported,USD,2026-04-01,2026-04-30,ACTIVE,1000",
            ",Missing Name,USD,2026-04-01,2026-04-30,ACTIVE,1200",
        ],
    )

    summary = importer.import_csv("projects", csv_path)

    assert summary.created_count == 1
    assert summary.updated_count == 0
    assert summary.error_count == 1
    assert "line 3" in summary.error_rows[0]
    assert any(project.name == "Good Project" for project in ps.list_projects())


def test_import_resources_updates_existing_rows_by_id_and_parses_false_boolean(services, workspace_dir):
    importer = services["data_import_service"]
    rs = services["resource_service"]

    resource = rs.create_resource("Import Dev", role="Developer", hourly_rate=100.0, capacity_percent=80.0)
    csv_path = _write_csv(
        workspace_dir,
        "resources.csv",
        [
            "id,name,role,hourly_rate,currency_code,capacity_percent,is_active,address,contact",
            f"{resource.id},Import Dev Senior,Architect,145,usd,65,no,Remote,dev@example.com",
        ],
    )

    summary = importer.import_csv("resources", csv_path)
    updated = rs.get_resource(resource.id)

    assert summary.updated_count == 1
    assert summary.error_count == 0
    assert updated.name == "Import Dev Senior"
    assert updated.role == "Architect"
    assert updated.hourly_rate == pytest.approx(145.0)
    assert updated.currency_code == "USD"
    assert updated.capacity_percent == pytest.approx(65.0)
    assert updated.is_active is False
    assert updated.address == "Remote"
    assert updated.contact == "dev@example.com"


def test_import_tasks_updates_existing_rows_and_reports_missing_project_reference(services, workspace_dir):
    importer = services["data_import_service"]
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Task Import Project")
    task = ts.create_task(project.id, "Imported Task", start_date=date(2026, 4, 1), duration_days=2)
    csv_path = _write_csv(
        workspace_dir,
        "tasks.csv",
        [
            "id,project_id,project_name,name,description,start_date,duration_days,status,priority,percent_complete",
            f"{task.id},{project.id},,Imported Task,Updated via CSV,2026-04-03,5,IN_PROGRESS,4,75",
            ",,,Broken Task,Missing project,2026-04-03,5,TODO,1,10",
        ],
    )

    summary = importer.import_csv("tasks", csv_path)
    updated = ts.get_task(task.id)

    assert summary.updated_count == 1
    assert summary.error_count == 1
    assert "Project reference is required" in summary.error_rows[0]
    assert updated.description == "Updated via CSV"
    assert updated.start_date == date(2026, 4, 3)
    assert updated.duration_days == 5
    assert updated.priority == 4
    assert updated.percent_complete == pytest.approx(75.0)


def test_import_costs_collects_invalid_rows_and_keeps_valid_rows(services, workspace_dir):
    importer = services["data_import_service"]
    ps = services["project_service"]
    ts = services["task_service"]
    cs = services["cost_service"]

    project = ps.create_project("Cost Import Project")
    task = ts.create_task(project.id, "Imported Cost Task", start_date=date(2026, 4, 2), duration_days=2)
    csv_path = _write_csv(
        workspace_dir,
        "costs.csv",
        [
            "project_name,task_name,description,planned_amount,actual_amount,currency_code,cost_type",
            "Cost Import Project,Imported Cost Task,Valid Cost,800,100,USD,LABOR",
            "Cost Import Project,Imported Cost Task,Bad Cost,500,100,USD,NOT_A_TYPE",
        ],
    )

    summary = importer.import_csv("costs", csv_path)
    costs = cs.list_cost_items_for_project(project.id)

    assert summary.created_count == 1
    assert summary.error_count == 1
    assert "line 3" in summary.error_rows[0]
    assert len(costs) == 1
    assert costs[0].task_id == task.id
    assert costs[0].description == "Valid Cost"


def test_import_csv_rejects_unknown_entity_types(services, workspace_dir):
    importer = services["data_import_service"]
    csv_path = _write_csv(workspace_dir, "noop.csv", ["name", "placeholder"])

    with pytest.raises(ValueError, match="Unsupported import type"):
        importer.import_csv("vendors", csv_path)


def test_initialize_timesheet_is_idempotent_for_legacy_hours(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Idempotent Timesheet")
    task = ts.create_task(project.id, "Idempotent Task", start_date=date(2026, 3, 10), duration_days=1)
    resource = rs.create_resource("Idempotent Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=50.0)
    ts.set_assignment_hours(assignment.id, 4.0)

    first = ts.initialize_timesheet_for_assignment(assignment.id)
    second = ts.initialize_timesheet_for_assignment(assignment.id)

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].id == second[0].id
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(4.0)


def test_add_time_entry_bootstraps_legacy_hours_without_explicit_initialize(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Implicit Bootstrap")
    task = ts.create_task(project.id, "Bootstrap Task", start_date=date(2026, 3, 11), duration_days=1)
    resource = rs.create_resource("Implicit Dev", hourly_rate=110.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=75.0)
    ts.set_assignment_hours(assignment.id, 5.0)

    ts.add_time_entry(assignment.id, entry_date=date(2026, 3, 12), hours=2.0, note="Follow-up work")
    entries = ts.list_time_entries_for_assignment(assignment.id)

    assert len(entries) == 2
    assert entries[0].author_username == "system"
    assert entries[0].hours == pytest.approx(5.0)
    assert entries[1].note == "Follow-up work"
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(7.0)


def test_unassigning_resource_removes_associated_time_entries(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Unassign Timesheet Cleanup")
    task = ts.create_task(project.id, "Cleanup Task", start_date=date(2026, 3, 13), duration_days=1)
    resource = rs.create_resource("Cleanup Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=40.0)
    ts.add_time_entry(assignment.id, entry_date=date(2026, 3, 13), hours=2.0, note="Cleanup")

    assert _time_entry_count(services) == 1

    ts.unassign_resource(assignment.id)

    assert _time_entry_count(services) == 0


def test_deleting_task_removes_associated_time_entries(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Delete Task Timesheet Cleanup")
    task = ts.create_task(project.id, "Cleanup Task", start_date=date(2026, 3, 14), duration_days=1)
    resource = rs.create_resource("Cleanup Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=40.0)
    ts.add_time_entry(assignment.id, entry_date=date(2026, 3, 14), hours=2.0, note="Cleanup")

    assert _time_entry_count(services) == 1

    ts.delete_task(task.id)

    assert _time_entry_count(services) == 0


def test_deleting_project_removes_time_entries_created_under_its_assignments(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Delete Project Timesheet Cleanup")
    task = ts.create_task(project.id, "Cleanup Task", start_date=date(2026, 3, 15), duration_days=1)
    resource = rs.create_resource("Cleanup Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=40.0)
    ts.add_time_entry(assignment.id, entry_date=date(2026, 3, 15), hours=2.0, note="Cleanup")

    assert _time_entry_count(services) == 1

    ps.delete_project(project.id)

    assert _time_entry_count(services) == 0


def test_deleting_resource_removes_time_entries_created_under_its_assignments(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Delete Resource Timesheet Cleanup")
    task = ts.create_task(project.id, "Cleanup Task", start_date=date(2026, 3, 16), duration_days=1)
    resource = rs.create_resource("Cleanup Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=40.0)
    ts.add_time_entry(assignment.id, entry_date=date(2026, 3, 16), hours=2.0, note="Cleanup")

    assert _time_entry_count(services) == 1

    rs.delete_resource(resource.id)

    assert _time_entry_count(services) == 0


def test_time_entry_hours_must_be_greater_than_zero(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Time Entry Validation")
    task = ts.create_task(project.id, "Validation Task", start_date=date(2026, 3, 17), duration_days=1)
    resource = rs.create_resource("Validation Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=25.0)

    with pytest.raises(ValidationError, match="greater than zero"):
        ts.add_time_entry(assignment.id, entry_date=date(2026, 3, 17), hours=0.0, note="Invalid")
