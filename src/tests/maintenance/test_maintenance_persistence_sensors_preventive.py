from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError


def test_maintenance_material_requirements_persist_and_escalate_via_service_graph(services):
    site = services["site_service"].create_site(
        site_code="MNT-MAT",
        name="Maintenance Material Plant",
        currency_code="EUR",
    )
    category = services["inventory_item_category_service"].create_category(
        category_code="MNT-SPARE",
        name="Maintenance Spare",
        category_type="SPARE",
        supports_maintenance_usage=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="MNT-STR",
        name="Maintenance Storeroom",
        site_id=site.id,
        status="ACTIVE",
    )
    item = services["inventory_item_service"].create_item(
        item_code="MNT-ITEM-100",
        name="Mechanical Seal Kit",
        status="ACTIVE",
        stock_uom="EA",
        category_code=category.category_code,
        is_stocked=False,
        is_purchase_allowed=True,
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="mat-area",
        name="Material Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="mat-asset",
        name="Material Asset",
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-mat-100",
        work_order_type="corrective",
        source_type="manual",
        asset_id=asset.id,
        location_id=location.id,
        title="Replace seal assembly",
    )

    requirement = services["maintenance_work_order_material_requirement_service"].create_requirement(
        work_order_id=work_order.id,
        stock_item_id=item.id,
        preferred_storeroom_id=storeroom.id,
        required_qty="3",
        notes="Seal kit demand",
    )
    refreshed = services["maintenance_work_order_material_requirement_service"].refresh_requirement_availability(
        requirement.id,
        expected_version=requirement.version,
    )
    escalation = services["maintenance_work_order_material_requirement_service"].escalate_requirement_shortage(
        requirement.id,
        expected_version=refreshed.version,
        notes="Escalate seal kit shortage",
    )
    reloaded = services["maintenance_work_order_material_requirement_service"].get_requirement(requirement.id)
    listed = services["maintenance_work_order_material_requirement_service"].list_requirements(
        work_order_id=work_order.id
    )

    assert refreshed.last_availability_status == "DIRECT_PROCUREMENT_ONLY"
    assert refreshed.procurement_status.value == "SHORTAGE_IDENTIFIED"
    assert escalation.requisition.id == reloaded.linked_requisition_id
    assert reloaded.procurement_status.value == "REQUISITIONED"
    assert [row.id for row in listed] == [requirement.id]


def test_maintenance_sensors_and_readings_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-SNS", name="Sensor Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="sns-area",
        name="Sensor Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="sns-asset",
        name="Sensor Asset",
    )

    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="hours-100",
        sensor_name="Running Hours 100",
        asset_id=asset.id,
        sensor_type="RUNNING_HOURS",
        source_type="IOT_GATEWAY",
        unit="H",
    )
    reading = services["maintenance_sensor_reading_service"].record_reading(
        sensor_id=sensor.id,
        reading_value="145.75",
        reading_unit="H",
        source_name="Gateway A",
        source_batch_id="SYNC-100",
    )

    reloaded_sensor = services["maintenance_sensor_service"].find_sensor_by_code("HOURS-100")
    listed_readings = services["maintenance_sensor_reading_service"].list_readings(sensor_id=sensor.id)

    assert reloaded_sensor is not None
    assert reloaded_sensor.id == sensor.id
    assert reloaded_sensor.current_value == reading.reading_value
    assert reloaded_sensor.last_read_at == reading.reading_timestamp.replace(tzinfo=None)
    assert listed_readings[0].id == reading.id
    assert listed_readings[0].source_batch_id == "SYNC-100"


def test_maintenance_preventive_templates_and_plans_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-PM", name="Preventive Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="pm-area",
        name="PM Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="pm-asset-100",
        name="Preventive Asset",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="pm-sensor-100",
        sensor_name="Runtime Hours",
        asset_id=asset.id,
        sensor_type="RUN_HOURS",
        unit="H",
    )
    task_template = services["maintenance_task_template_service"].create_task_template(
        task_template_code="pm-lube-100",
        name="Lubricate Drive End",
        maintenance_type="preventive",
        template_status="active",
        estimated_minutes=35,
        required_skill="MECHANICAL",
    )
    step_template = services["maintenance_task_step_template_service"].create_step_template(
        task_template_id=task_template.id,
        step_number=1,
        instruction="Apply grease to the drive-end bearing.",
        requires_confirmation=True,
    )
    plan = services["maintenance_preventive_plan_service"].create_preventive_plan(
        site_id=site.id,
        plan_code="pm-plan-100",
        name="Drive-End Lubrication Plan",
        asset_id=asset.id,
        plan_type="preventive",
        trigger_mode="hybrid",
        calendar_frequency_unit="monthly",
        calendar_frequency_value=1,
        sensor_id=sensor.id,
        sensor_threshold="250.0",
        sensor_direction="greater_or_equal",
        auto_generate_work_order=True,
    )
    plan_task = services["maintenance_preventive_plan_task_service"].create_plan_task(
        plan_id=plan.id,
        task_template_id=task_template.id,
        sequence_no=1,
        trigger_scope="inherit_plan",
    )

    reloaded_template = services["maintenance_task_template_service"].find_task_template_by_code("PM-LUBE-100")
    reloaded_plan = services["maintenance_preventive_plan_service"].find_preventive_plan_by_code("PM-PLAN-100")
    step_rows = services["maintenance_task_step_template_service"].list_step_templates(
        task_template_id=task_template.id
    )
    plan_task_rows = services["maintenance_preventive_plan_task_service"].list_plan_tasks(plan_id=plan.id)

    assert reloaded_template is not None
    assert reloaded_template.id == task_template.id
    assert reloaded_template.required_skill == "MECHANICAL"
    assert reloaded_plan is not None
    assert reloaded_plan.id == plan.id
    assert reloaded_plan.sensor_id == sensor.id
    assert reloaded_plan.trigger_mode.value == "HYBRID"
    assert [row.id for row in step_rows] == [step_template.id]
    assert step_rows[0].requires_confirmation is True
    assert [row.id for row in plan_task_rows] == [plan_task.id]
    assert plan_task_rows[0].trigger_scope.value == "INHERIT_PLAN"
