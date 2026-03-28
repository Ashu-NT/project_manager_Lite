from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from core.platform.auth.session import UserSessionPrincipal
from core.platform.common.exceptions import BusinessRuleError
from core.platform.time.domain import TimesheetPeriodStatus
from core.platform.common.exceptions import ValidationError
from core.modules.project_management.domain.enums import WorkerType
from tests.temp_dirs import cleanup_test_workspace, create_test_workspace


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


def test_legacy_assignment_hours_seed_opening_balance_before_timesheet_lock(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Legacy Hours Project")
    task = ts.create_task(project.id, "Legacy Hours Task", start_date=date(2026, 3, 4), duration_days=2)
    resource = rs.create_resource("Legacy Logger", hourly_rate=95.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=60.0)

    ts.set_assignment_hours(assignment.id, 4.0)
    seeded_entries = ts.initialize_timesheet_for_assignment(assignment.id)

    assert len(seeded_entries) == 1
    assert seeded_entries[0].hours == pytest.approx(4.0)
    assert seeded_entries[0].entry_date == date(2026, 3, 4)
    assert seeded_entries[0].author_username == "system"
    assert "Opening balance" in seeded_entries[0].note

    ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 3, 5),
        hours=2.0,
        note="Testing",
    )

    entries = ts.list_time_entries_for_assignment(assignment.id)
    assert len(entries) == 2
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(6.0)

    with pytest.raises(ValidationError, match="timesheet"):
        ts.set_assignment_hours(assignment.id, 8.0)


def test_time_entries_capture_platform_work_entry_context_for_employee_resources(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    es = services["employee_service"]
    site = services["site_service"].create_site(site_code="HAM", name="Hamburg Yard")
    department = services["department_service"].create_department(
        department_code="OPS",
        name="Operations",
        site_id=site.id,
    )

    employee = es.create_employee(
        employee_code="EMP-101",
        full_name="Context Owner",
        department_id=department.id,
        department="Operations",
        site_id=site.id,
        site_name="Hamburg Yard",
        title="Technician",
        email="context.owner@example.com",
    )
    project = ps.create_project("Shared Time Context")
    task = ts.create_task(project.id, "Log Shared Work", start_date=date(2026, 8, 4), duration_days=2)
    resource = rs.create_resource(
        "",
        hourly_rate=88.0,
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)

    entry = ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 8, 4),
        hours=5.0,
        note="Shared platform work entry snapshot",
    )

    assert entry.work_allocation_id == assignment.id
    assert entry.assignment_id == assignment.id
    assert entry.owner_type == "task_assignment"
    assert entry.owner_id == assignment.id
    assert entry.owner_label == task.name
    assert entry.scope_type == "project"
    assert entry.scope_id == project.id
    assert entry.employee_id == employee.id
    assert entry.department_id == department.id
    assert entry.department_name == "Operations"
    assert entry.site_id == site.id
    assert entry.site_name == "Hamburg Yard"


def test_shared_time_work_allocation_aliases_preserve_pm_timesheet_flows(services):
    ps = services["project_service"]
    ts = services["task_service"]
    timesheet_service = services["timesheet_service"]
    rs = services["resource_service"]

    project = ps.create_project("Shared Time Alias Project")
    task = ts.create_task(project.id, "Alias Task", start_date=date(2026, 9, 1), duration_days=2)
    resource = rs.create_resource("Alias Resource", hourly_rate=105.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)

    entry = timesheet_service.add_work_entry(
        assignment.id,
        entry_date=date(2026, 9, 1),
        hours=4.0,
        note="Shared work allocation entry",
    )

    listed = timesheet_service.list_time_entries_for_work_allocation(assignment.id)
    listed_period = timesheet_service.list_time_entries_for_work_allocation_period(
        assignment.id,
        period_start=date(2026, 9, 15),
    )

    assert entry.work_allocation_id == assignment.id
    assert entry.assignment_id == assignment.id
    assert entry.owner_label == task.name
    assert entry.scope_type == "project"
    assert entry.scope_id == project.id
    assert [row.id for row in listed] == [entry.id]
    assert [row.id for row in listed_period] == [entry.id]


def test_timesheet_period_submission_blocks_edits_for_that_month_only(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Timesheet Approval Project")
    task = ts.create_task(project.id, "Approval Task", start_date=date(2026, 3, 1), duration_days=5)
    resource = rs.create_resource("Submitted Dev", hourly_rate=100.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)

    march_entry = ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 3, 5),
        hours=4.0,
        note="March work",
    )
    april_entry = ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 4, 2),
        hours=2.5,
        note="April work",
    )

    period = ts.submit_timesheet_period(
        resource.id,
        period_start=date(2026, 3, 15),
        note="Ready for review",
    )

    assert period.status == TimesheetPeriodStatus.SUBMITTED
    assert period.period_start == date(2026, 3, 1)
    assert len(ts.list_time_entries_for_resource_period(resource.id, period_start=date(2026, 3, 1))) == 1

    with pytest.raises(ValidationError, match="submitted"):
        ts.add_time_entry(
            assignment.id,
            entry_date=date(2026, 3, 6),
            hours=1.0,
            note="Blocked follow-up",
        )
    with pytest.raises(ValidationError, match="submitted"):
        ts.update_time_entry(march_entry.id, hours=5.0)
    with pytest.raises(ValidationError, match="submitted"):
        ts.delete_time_entry(march_entry.id)

    ts.update_time_entry(april_entry.id, hours=3.0, note="April still editable")
    assert ts.get_assignment(assignment.id).hours_logged == pytest.approx(7.0)


def test_timesheet_period_lock_unlock_and_approval_state_transitions(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Timesheet Lock Project")
    task = ts.create_task(project.id, "Lock Task", start_date=date(2026, 5, 1), duration_days=3)
    resource = rs.create_resource("Locked Dev", hourly_rate=90.0)
    assignment = ts.assign_resource(task.id, resource.id, allocation_percent=100.0)
    may_entry = ts.add_time_entry(
        assignment.id,
        entry_date=date(2026, 5, 3),
        hours=6.0,
        note="May work",
    )

    locked = ts.lock_timesheet_period(
        resource.id,
        period_start=date(2026, 5, 20),
        note="Payroll closed",
    )
    assert locked.status == TimesheetPeriodStatus.LOCKED

    with pytest.raises(ValidationError, match="locked"):
        ts.update_time_entry(may_entry.id, hours=6.5)

    unlocked = ts.unlock_timesheet_period(locked.id, note="Correction window")
    assert unlocked.status == TimesheetPeriodStatus.OPEN

    submitted = ts.submit_timesheet_period(resource.id, period_start=date(2026, 5, 1))
    approved = ts.approve_timesheet_period(submitted.id, note="Approved for payroll")
    assert approved.status == TimesheetPeriodStatus.APPROVED
    assert approved.locked_at is not None

    with pytest.raises(ValidationError, match="approved"):
        ts.update_time_entry(may_entry.id, hours=7.0)


def test_data_import_service_imports_projects_resources_tasks_and_costs(services):
    importer = services["data_import_service"]
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]
    cs = services["cost_service"]

    tmp = create_test_workspace("import")
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
        cleanup_test_workspace(tmp)


def test_data_import_service_requires_import_manage_permission_from_live_session(services):
    importer = services["data_import_service"]
    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id="u-import",
            username="pm-reader",
            display_name="PM Reader",
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"project.read"}),
        )
    )

    with pytest.raises(BusinessRuleError, match="Permission denied") as exc:
        importer.get_import_schema("projects")

    assert exc.value.code == "PERMISSION_DENIED"
