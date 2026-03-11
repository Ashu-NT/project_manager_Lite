from __future__ import annotations

from datetime import date

from tests.ui_runtime_helpers import login_as, register_and_login
from ui.timesheet.dialog import TimesheetDialog


def _build_timesheet_context(services):
    project = services["project_service"].create_project("Timesheet UI Project")
    task_service = services["task_service"]
    timesheet_service = services["timesheet_service"]
    resource_service = services["resource_service"]
    project_resource_service = services["project_resource_service"]

    task_a = task_service.create_task(
        project.id,
        "Design API",
        start_date=date(2026, 6, 2),
        duration_days=2,
    )
    task_b = task_service.create_task(
        project.id,
        "Build UI",
        start_date=date(2026, 6, 4),
        duration_days=2,
    )
    resource = resource_service.create_resource("Timesheet User", hourly_rate=100.0)
    project_resource = project_resource_service.add_to_project(project.id, resource.id, hourly_rate=100.0)

    assignment_a = task_service.assign_project_resource(task_a.id, project_resource.id, 50.0)
    assignment_b = task_service.assign_project_resource(task_b.id, project_resource.id, 50.0)

    timesheet_service.add_time_entry(
        assignment_a.id,
        entry_date=date(2026, 6, 3),
        hours=4.0,
        note="API design",
    )
    timesheet_service.add_time_entry(
        assignment_b.id,
        entry_date=date(2026, 6, 4),
        hours=3.0,
        note="UI build",
    )

    return {
        "project": project,
        "resource": resource,
        "task_a": task_a,
        "assignment_a": assignment_a,
        "assignment_b": assignment_b,
    }


def test_task_service_timesheet_bridge_uses_dedicated_service_backend(services):
    ctx = _build_timesheet_context(services)

    bridged_entries = services["task_service"].list_time_entries_for_assignment(ctx["assignment_a"].id)
    direct_entries = services["timesheet_service"].list_time_entries_for_assignment(ctx["assignment_a"].id)

    assert [entry.id for entry in bridged_entries] == [entry.id for entry in direct_entries]
    assert services["task_service"].get_timesheet_period(
        ctx["resource"].id,
        period_start=date(2026, 6, 1),
    ) == services["timesheet_service"].get_timesheet_period(
        ctx["resource"].id,
        period_start=date(2026, 6, 1),
    )


def test_timesheet_dialog_scopes_task_rows_but_shows_full_resource_period_total(
    qapp,
    services,
):
    ctx = _build_timesheet_context(services)

    dialog = TimesheetDialog(
        None,
        timesheet_service=services["timesheet_service"],
        assignment=ctx["assignment_a"],
        task_name=ctx["task_a"].name,
        resource_name=ctx["resource"].name,
        user_session=services["user_session"],
    )

    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 3).text() == "API design"
    assert "Task period entries: 1 | Task hours: 4.00" == dialog.summary_label.text()
    assert "Resource period total: 7.00 hours across 2 entries." in dialog.scope_label.text()
    assert "Period June 2026 status: OPEN" == dialog.period_status_label.text()
    assert dialog.btn_submit.isEnabled() is True
    assert dialog.btn_approve.isEnabled() is False


def test_timesheet_dialog_period_actions_run_through_runtime_ui(
    qapp,
    services,
    monkeypatch,
):
    ctx = _build_timesheet_context(services)
    services["timesheet_service"].add_time_entry(
        ctx["assignment_a"].id,
        entry_date=date(2026, 7, 2),
        hours=2.0,
        note="July wrap-up",
    )
    notes = iter(
        [
            ("Submit June", True),
            ("Needs correction", True),
            ("Resubmit June", True),
            ("Approved for payroll", True),
            ("Freeze July", True),
            ("Reopen July", True),
        ]
    )
    monkeypatch.setattr(
        "ui.timesheet.dialog.QInputDialog.getMultiLineText",
        lambda *_args, **_kwargs: next(notes),
    )

    dialog = TimesheetDialog(
        None,
        timesheet_service=services["timesheet_service"],
        assignment=ctx["assignment_a"],
        task_name=ctx["task_a"].name,
        resource_name=ctx["resource"].name,
        user_session=services["user_session"],
    )
    dialog.period_edit.setDate(dialog.period_edit.date().addMonths(-1))

    dialog._submit_period()
    submitted = services["timesheet_service"].get_timesheet_period(ctx["resource"].id, period_start=date(2026, 6, 1))
    assert submitted is not None
    assert submitted.status.value == "SUBMITTED"
    assert dialog.btn_add.isEnabled() is False
    assert dialog.btn_approve.isEnabled() is True

    dialog._reject_period()
    rejected = services["timesheet_service"].get_timesheet_period(ctx["resource"].id, period_start=date(2026, 6, 1))
    assert rejected is not None
    assert rejected.status.value == "REJECTED"
    assert dialog.btn_add.isEnabled() is True
    assert dialog.btn_submit.isEnabled() is True

    dialog._submit_period()
    dialog._approve_period()
    approved = services["timesheet_service"].get_timesheet_period(ctx["resource"].id, period_start=date(2026, 6, 1))
    assert approved is not None
    assert approved.status.value == "APPROVED"
    assert "APPROVED" in dialog.period_status_label.text()
    assert dialog.btn_submit.isEnabled() is False
    assert dialog.btn_lock.isEnabled() is False

    dialog.period_edit.setDate(dialog.period_edit.date().addMonths(1))
    dialog._lock_period()
    locked = services["timesheet_service"].get_timesheet_period(ctx["resource"].id, period_start=date(2026, 7, 1))
    assert locked is not None
    assert locked.status.value == "LOCKED"
    assert dialog.btn_add.isEnabled() is False
    assert dialog.btn_unlock.isEnabled() is True

    dialog._unlock_period()
    reopened = services["timesheet_service"].get_timesheet_period(ctx["resource"].id, period_start=date(2026, 7, 1))
    assert reopened is not None
    assert reopened.status.value == "OPEN"
    assert dialog.btn_add.isEnabled() is True


def test_timesheet_dialog_permission_states_distinguish_planner_from_admin(
    qapp,
    services,
):
    ctx = _build_timesheet_context(services)
    register_and_login(services, username_prefix="planner-timesheet", role_names=("planner",))

    planner_dialog = TimesheetDialog(
        None,
        timesheet_service=services["timesheet_service"],
        assignment=ctx["assignment_a"],
        task_name=ctx["task_a"].name,
        resource_name=ctx["resource"].name,
        user_session=services["user_session"],
    )

    assert planner_dialog.btn_submit.isEnabled() is True
    assert planner_dialog.btn_approve.isEnabled() is False
    assert planner_dialog.btn_lock.isEnabled() is False

    login_as(services, "admin", "ChangeMe123!")
    admin_dialog = TimesheetDialog(
        None,
        timesheet_service=services["timesheet_service"],
        assignment=ctx["assignment_a"],
        task_name=ctx["task_a"].name,
        resource_name=ctx["resource"].name,
        user_session=services["user_session"],
    )

    assert admin_dialog.btn_lock.isEnabled() is True


def test_timesheet_dialog_surfaces_period_review_lane_and_navigation(
    qapp,
    services,
    monkeypatch,
):
    ctx = _build_timesheet_context(services)
    notes = iter(
        [
            ("Submit June", True),
            ("Freeze July", True),
        ]
    )
    monkeypatch.setattr(
        "ui.timesheet.dialog.QInputDialog.getMultiLineText",
        lambda *_args, **_kwargs: next(notes),
    )
    services["timesheet_service"].add_time_entry(
        ctx["assignment_a"].id,
        entry_date=date(2026, 7, 6),
        hours=2.5,
        note="July execution",
    )
    services["timesheet_service"].submit_timesheet_period(
        ctx["resource"].id,
        period_start=date(2026, 6, 1),
        note="Ready for approval",
    )
    services["timesheet_service"].lock_timesheet_period(
        ctx["resource"].id,
        period_start=date(2026, 7, 1),
        note="Payroll close",
    )

    dialog = TimesheetDialog(
        None,
        timesheet_service=services["timesheet_service"],
        assignment=ctx["assignment_a"],
        task_name=ctx["task_a"].name,
        resource_name=ctx["resource"].name,
        user_session=services["user_session"],
    )
    dialog.period_edit.setDate(dialog.period_edit.date().addMonths(-1))

    assert dialog.period_table.rowCount() >= 2
    assert "Approval queue" in dialog.period_queue_label.text()
    assert dialog.period_badge.text() == "SUBMITTED"

    dialog.period_table.selectRow(0)
    selected_period = dialog._current_period_start()
    assert selected_period in {date(2026, 6, 1), date(2026, 7, 1)}
