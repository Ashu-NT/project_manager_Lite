from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError


def test_maintenance_work_request_and_work_order_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-WORK", name="Maintenance Work Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="wrk-area",
        name="Work Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="wrk-asset",
        name="Work Asset",
    )

    work_request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-100",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        title="Seal leak",
        priority="high",
    )
    reloaded_work_request = services["maintenance_work_request_service"].find_work_request_by_code("WR-100")
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-100",
        work_order_type="corrective",
        source_type="work_request",
        source_id=work_request.id,
        assigned_team_id="TEAM-A",
    )
    reloaded_work_order = services["maintenance_work_order_service"].find_work_order_by_code("WO-100")
    converted_work_request = services["maintenance_work_request_service"].get_work_request(work_request.id)

    assert reloaded_work_request is not None
    assert reloaded_work_request.id == work_request.id
    assert reloaded_work_request.source_type.value == "MANUAL"
    assert reloaded_work_request.source_id is None
    assert reloaded_work_request.source_plan_task_ids == ()
    assert reloaded_work_request.request_type == "BREAKDOWN"
    assert converted_work_request.status.value == "CONVERTED"
    assert reloaded_work_order is not None
    assert reloaded_work_order.id == work_order.id
    assert reloaded_work_order.work_order_type.value == "CORRECTIVE"
    assert reloaded_work_order.asset_id == asset.id
    assert reloaded_work_order.location_id == location.id
    assert reloaded_work_order.assigned_team_id == "TEAM-A"


def test_maintenance_work_order_updates_persist_status_and_assignment(services):
    site = services["site_service"].create_site(site_code="MNT-WORK-UPD", name="Maintenance Update Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="upd-area",
        name="Update Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="upd-asset",
        name="Update Asset",
    )
    work_request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-upd-100",
        source_type="manual",
        request_type="inspection",
        asset_id=asset.id,
        location_id=location.id,
        title="Inspect gearbox",
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-upd-100",
        work_order_type="inspection",
        source_type="work_request",
        source_id=work_request.id,
    )

    planned = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="PLANNED",
        assigned_team_id="TEAM-B",
        expected_version=work_order.version,
    )
    released = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="RELEASED",
        expected_version=planned.version,
    )
    started = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="IN_PROGRESS",
        expected_version=released.version,
    )
    completed = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="COMPLETED",
        expected_version=started.version,
    )
    closed = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="CLOSED",
        expected_version=completed.version,
    )

    assert planned.assigned_team_id == "TEAM-B"
    assert started.actual_start is not None
    assert completed.actual_end is not None
    assert closed.closed_at is not None
    assert closed.closed_by_user_id == services["user_session"].principal.user_id
    assert closed.version == 6


def test_maintenance_work_order_tasks_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-WOTASK", name="Maintenance Task Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="task-area",
        name="Task Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="task-asset",
        name="Task Asset",
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-task-100",
        work_order_type="corrective",
        source_type="manual",
        asset_id=asset.id,
        location_id=location.id,
        title="Repair fan",
    )

    first_task = services["maintenance_work_order_task_service"].create_task(
        work_order_id=work_order.id,
        task_name="Isolate power",
        assigned_team_id="TEAM-LOCKOUT",
        estimated_minutes=20,
    )
    second_task = services["maintenance_work_order_task_service"].create_task(
        work_order_id=work_order.id,
        task_name="Replace bearing",
        estimated_minutes=45,
    )
    started_task = services["maintenance_work_order_task_service"].update_task(
        first_task.id,
        status="IN_PROGRESS",
        expected_version=first_task.version,
    )
    completed_task = services["maintenance_work_order_task_service"].update_task(
        first_task.id,
        status="COMPLETED",
        actual_minutes=18,
        expected_version=started_task.version,
    )
    listed_tasks = services["maintenance_work_order_task_service"].list_tasks(work_order_id=work_order.id)

    assert second_task.sequence_no == first_task.sequence_no + 1
    assert completed_task.actual_minutes == 18
    assert completed_task.completed_at is not None
    assert [row.sequence_no for row in listed_tasks] == [1, 2]
    assert listed_tasks[0].id == first_task.id


def test_maintenance_work_order_task_steps_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-WOSTEP", name="Maintenance Step Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="step-area",
        name="Step Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="step-asset",
        name="Step Asset",
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-step-100",
        work_order_type="corrective",
        source_type="manual",
        asset_id=asset.id,
        location_id=location.id,
        title="Restore pump alignment",
    )
    task = services["maintenance_work_order_task_service"].create_task(
        work_order_id=work_order.id,
        task_name="Set final alignment",
        completion_rule="all_steps_required",
    )

    confirm_step = services["maintenance_work_order_task_step_service"].create_step(
        work_order_task_id=task.id,
        instruction="Confirm coupling seating",
        requires_confirmation=True,
    )
    measure_step = services["maintenance_work_order_task_step_service"].create_step(
        work_order_task_id=task.id,
        instruction="Capture final vibration",
        requires_measurement=True,
        measurement_unit="MM/S",
    )

    done_confirm_step = services["maintenance_work_order_task_step_service"].update_step(
        confirm_step.id,
        status="DONE",
        expected_version=confirm_step.version,
    )
    confirmed_step = services["maintenance_work_order_task_step_service"].update_step(
        confirm_step.id,
        confirm_completion=True,
        expected_version=done_confirm_step.version,
    )
    done_measure_step = services["maintenance_work_order_task_step_service"].update_step(
        measure_step.id,
        measurement_value="2.3",
        status="DONE",
        expected_version=measure_step.version,
    )
    completed_task = services["maintenance_work_order_task_service"].update_task(
        task.id,
        status="COMPLETED",
        expected_version=task.version,
    )
    listed_steps = services["maintenance_work_order_task_step_service"].list_steps(work_order_task_id=task.id)

    assert confirmed_step.confirmed_at is not None
    assert confirmed_step.confirmed_by_user_id == services["user_session"].principal.user_id
    assert done_measure_step.measurement_value == "2.3"
    assert completed_task.status.value == "COMPLETED"
    assert [row.step_number for row in listed_steps] == [1, 2]
