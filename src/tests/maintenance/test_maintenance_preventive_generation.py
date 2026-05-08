from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def test_preventive_generation_creates_work_order_and_copies_templates(services):
    site = services["site_service"].create_site(site_code="MNT-GEN", name="Generation Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="gen-area",
        name="Generation Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="gen-asset",
        name="Generation Asset",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="gen-hours",
        sensor_name="Run Hours",
        asset_id=asset.id,
        sensor_type="RUN_HOURS",
        unit="H",
        current_value="260",
        last_read_at=datetime.now(timezone.utc),
        last_quality_state="VALID",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="gen-task",
        name="Lubricate bearings",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=30,
        required_skill="MECHANICAL",
    )
    step_template = services["maintenance_task_step_template_service"].create_step_template(
        task_template_id=task_template.id,
        step_number=1,
        instruction="Apply grease to both bearing points.",
        expected_result="Fresh grease visible at relief point.",
        requires_confirmation=True,
    )
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="gen-plan",
        name="Bearing Lubrication Plan",
        asset_id=asset.id,
        status="active",
        plan_type="preventive",
        trigger_mode="hybrid",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        sensor_id=sensor.id,
        sensor_threshold="250",
        sensor_direction="greater_or_equal",
        auto_generate_work_order=True,
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )

    candidates = services["maintenance_preventive_generation_service"].list_due_candidates(plan_id=plan.id)
    result = services["maintenance_preventive_generation_service"].generate_due_work(plan_id=plan.id)[0]

    assert candidates[0].due_state == "DUE"
    assert candidates[0].selected_plan_task_ids
    assert result.generated_work_order_id is not None
    assert result.generated_work_request_id is None
    assert len(result.generated_task_ids) == 1
    assert len(result.generated_step_ids) == 1

    work_order = services["maintenance_work_order_service"].get_work_order(result.generated_work_order_id)
    tasks = services["maintenance_work_order_task_service"].list_tasks(work_order_id=work_order.id)
    steps = services["maintenance_work_order_task_step_service"].list_steps(work_order_task_id=tasks[0].id)
    refreshed_plan = services["maintenance_preventive_plan_service"].find_preventive_plan_by_code("GEN-PLAN")

    assert work_order.source_type == "PREVENTIVE_PLAN"
    assert work_order.source_id == plan.id
    assert work_order.is_preventive is True
    assert tasks[0].task_template_id == task_template.id
    assert tasks[0].task_name == "Lubricate bearings"
    assert steps[0].source_step_template_id == step_template.id
    assert steps[0].instruction == "Apply grease to both bearing points."
    assert refreshed_plan is not None
    assert refreshed_plan.last_generated_at is not None
    assert refreshed_plan.next_due_counter == Decimal("500")


def test_preventive_generation_does_not_duplicate_sensor_due_work_without_new_threshold(services):
    site = services["site_service"].create_site(site_code="MNT-GEN2", name="Generation Plant 2")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="gen2-area",
        name="Generation Area 2",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="gen2-asset",
        name="Generation Asset 2",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="gen2-hours",
        sensor_name="Run Hours 2",
        asset_id=asset.id,
        sensor_type="RUN_HOURS",
        unit="H",
        current_value="300",
        last_read_at=datetime.now(timezone.utc),
        last_quality_state="VALID",
    )
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="gen2-plan",
        name="Duplicate Guard Plan",
        asset_id=asset.id,
        status="active",
        plan_type="preventive",
        trigger_mode="sensor",
        sensor_id=sensor.id,
        sensor_threshold="250",
        sensor_direction="greater_or_equal",
        auto_generate_work_order=True,
    )

    first = services["maintenance_preventive_generation_service"].generate_due_work(plan_id=plan.id)[0]
    second = services["maintenance_preventive_generation_service"].generate_due_work(plan_id=plan.id)[0]
    work_orders = services["maintenance_work_order_service"].list_work_orders(site_id=site.id, is_preventive=True)

    assert first.generated_work_order_id is not None
    assert second.generated_work_order_id is None
    assert second.skipped_reason
    assert len(work_orders) == 1


def test_preventive_generation_supports_due_task_override_without_plan_due(services):
    site = services["site_service"].create_site(site_code="MNT-GEN3", name="Generation Plant 3")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="gen3-area",
        name="Generation Area 3",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="gen3-asset",
        name="Generation Asset 3",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="gen3-vib",
        sensor_name="Vibration",
        asset_id=asset.id,
        sensor_type="VIBRATION",
        unit="MM/S",
        current_value="8.5",
        last_read_at=datetime.now(timezone.utc),
        last_quality_state="VALID",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="gen3-task",
        name="Check coupling",
        maintenance_type="inspection",
        template_status="active",
    )
    future_due = datetime.now(timezone.utc) + timedelta(days=30)
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="gen3-plan",
        name="Override Plan",
        asset_id=asset.id,
        status="active",
        plan_type="inspection",
        trigger_mode="calendar",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        next_due_at=future_due,
        auto_generate_work_order=True,
    )
    plan_task = services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="task_override",
        trigger_mode_override="sensor",
        sensor_id_override=sensor.id,
        sensor_threshold_override="7.5",
        sensor_direction_override="greater_or_equal",
    )

    candidate = services["maintenance_preventive_generation_service"].list_due_candidates(plan_id=plan.id)[0]
    result = services["maintenance_preventive_generation_service"].generate_due_work(plan_id=plan.id)[0]
    refreshed_task = services["maintenance_preventive_plan_task_service"].get_plan_task(plan_task.id)

    assert candidate.due_state == "DUE"
    assert candidate.selected_plan_task_ids == (plan_task.id,)
    assert result.generated_work_order_id is not None
    assert refreshed_task.last_generated_at is not None
    assert refreshed_task.next_due_counter == Decimal("15.0")


def test_preventive_request_conversion_populates_work_order_from_source_plan(services):
    site = services["site_service"].create_site(site_code="MNT-GEN4", name="Generation Plant 4")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="gen4-area",
        name="Generation Area 4",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="gen4-asset",
        name="Generation Asset 4",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="gen4-task",
        name="Inspect drive coupling",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=40,
        required_skill="MECHANICAL",
    )
    step_template = services["maintenance_task_step_template_service"].create_step_template(
        task_template_id=task_template.id,
        step_number=1,
        instruction="Check alignment and tighten set screws.",
        expected_result="Drive coupling aligned and secured.",
        requires_confirmation=True,
    )
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="gen4-plan",
        name="Drive Coupling PM",
        asset_id=asset.id,
        status="active",
        plan_type="preventive",
        trigger_mode="calendar",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        next_due_at=datetime.now(timezone.utc) - timedelta(days=1),
        auto_generate_work_order=False,
    )
    plan_task = services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )

    result = services["maintenance_preventive_generation_service"].generate_due_work(plan_id=plan.id)[0]
    work_request = services["maintenance_work_request_service"].get_work_request(result.generated_work_request_id)
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="gen4-wo",
        work_order_type="preventive",
        source_type="work_request",
        source_id=work_request.id,
    )
    tasks = services["maintenance_work_order_task_service"].list_tasks(work_order_id=work_order.id)
    steps = services["maintenance_work_order_task_step_service"].list_steps(work_order_task_id=tasks[0].id)

    assert result.generated_work_request_id is not None
    assert result.generated_work_order_id is None
    assert work_request.source_id == plan.id
    assert work_request.source_plan_task_ids == (plan_task.id,)
    assert work_order.is_preventive is True
    assert tasks[0].task_template_id == task_template.id
    assert tasks[0].task_name == "Inspect drive coupling"
    assert steps[0].source_step_template_id == step_template.id
    assert steps[0].instruction == "Check alignment and tighten set screws."


def test_preventive_request_conversion_completion_updates_preventive_instance(services):
    site = services["site_service"].create_site(site_code="MNT-GEN5", name="Generation Plant 5")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="gen5-area",
        name="Generation Area 5",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="gen5-asset",
        name="Generation Asset 5",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="gen5-task",
        name="Check lubrication points",
        maintenance_type="preventive",
        template_status="active",
    )
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="gen5-plan",
        name="Lubrication PM",
        asset_id=asset.id,
        status="active",
        plan_type="preventive",
        trigger_mode="calendar",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        next_due_at=datetime.now(timezone.utc) - timedelta(days=2),
        auto_generate_work_order=False,
    )
    services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )

    result = services["maintenance_preventive_generation_service"].generate_due_work(plan_id=plan.id)[0]
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="gen5-wo",
        work_order_type="preventive",
        source_type="work_request",
        source_id=result.generated_work_request_id,
    )
    planned = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        status="PLANNED",
        expected_version=work_order.version,
    )
    released = services["maintenance_work_order_service"].update_work_order(
        planned.id,
        status="RELEASED",
        expected_version=planned.version,
    )
    started = services["maintenance_work_order_service"].update_work_order(
        released.id,
        status="IN_PROGRESS",
        expected_version=released.version,
    )
    completed = services["maintenance_work_order_service"].update_work_order(
        started.id,
        status="COMPLETED",
        expected_version=started.version,
    )

    forecast_rows = services["maintenance_preventive_generation_service"].preview_plan_schedule(plan_id=plan.id)
    matching_rows = [
        row
        for row in forecast_rows
        if row.generated_work_request_id == result.generated_work_request_id
    ]

    assert completed.is_preventive is True
    assert len(matching_rows) == 1
    assert matching_rows[0].generated_work_request_id == result.generated_work_request_id
    assert matching_rows[0].generated_work_order_id == work_order.id
    assert matching_rows[0].instance_status == "COMPLETED"
    assert matching_rows[0].completed_at is not None
