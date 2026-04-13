from __future__ import annotations

from datetime import date

from core.platform.common.exceptions import ValidationError


def test_maintenance_services_persist_locations_systems_and_assets_via_service_graph(services):
    site = services["site_service"].create_site(
        site_code="MNT-PLANT",
        name="Maintenance Plant",
        city="Berlin",
    )
    manufacturer = services["party_service"].create_party(
        party_code="MFG-PLANT",
        party_name="Maintenance Maker",
        party_type="MANUFACTURER",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-PLANT",
        party_name="Maintenance Supplier",
        party_type="SUPPLIER",
    )

    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="boiler-house",
        name="Boiler House",
        location_type="AREA",
    )
    reloaded_location = services["maintenance_location_service"].find_location_by_code("BOILER-HOUSE")

    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        system_code="steam-main",
        name="Steam Main",
        location_id=location.id,
        system_type="UTILITY",
    )
    reloaded_system = services["maintenance_system_service"].find_system_by_code("STEAM-MAIN")
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="pump-100",
        name="Feed Pump 100",
        system_id=system.id,
        asset_type="PUMP",
        asset_category="ROTATING",
        manufacturer_party_id=manufacturer.id,
        supplier_party_id=supplier.id,
        install_date=date(2024, 1, 10),
        commission_date=date(2024, 1, 12),
        expected_life_years=10,
        replacement_cost="22000.00",
        maintenance_strategy="PM",
        service_level="HIGH",
        requires_shutdown_for_major_work=True,
    )
    reloaded_asset = services["maintenance_asset_service"].find_asset_by_code("PUMP-100")
    component = services["maintenance_asset_component_service"].create_component(
        asset_id=asset.id,
        component_code="seal-100",
        name="Seal Cartridge 100",
        component_type="SEAL",
        supplier_part_number="SEAL-PO-100",
        expected_life_hours=9000,
        is_critical_component=True,
    )
    reloaded_component = services["maintenance_asset_component_service"].find_component_by_code("SEAL-100")

    assert reloaded_location is not None
    assert reloaded_location.id == location.id
    assert reloaded_location.location_code == "BOILER-HOUSE"
    assert reloaded_location.version == 1
    assert reloaded_system is not None
    assert reloaded_system.id == system.id
    assert reloaded_system.location_id == location.id
    assert reloaded_system.system_code == "STEAM-MAIN"
    assert reloaded_asset is not None
    assert reloaded_asset.id == asset.id
    assert reloaded_asset.system_id == system.id
    assert reloaded_asset.location_id == location.id
    assert reloaded_asset.asset_code == "PUMP-100"
    assert reloaded_asset.requires_shutdown_for_major_work is True
    assert reloaded_component is not None
    assert reloaded_component.id == component.id
    assert reloaded_component.asset_id == asset.id
    assert reloaded_component.component_code == "SEAL-100"
    assert reloaded_component.is_critical_component is True


def test_maintenance_services_use_persistent_versioned_updates(services):
    site = services["site_service"].create_site(
        site_code="MNT-UPD",
        name="Update Plant",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="shop-1",
        name="Workshop 1",
    )
    manufacturer = services["party_service"].create_party(
        party_code="MFG-UPD",
        party_name="Update Maker",
        party_type="MANUFACTURER",
    )

    updated_location = services["maintenance_location_service"].update_location(
        location.id,
        name="Workshop Alpha",
        expected_version=location.version,
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="asset-upd",
        name="Update Asset",
        manufacturer_party_id=manufacturer.id,
    )
    updated_asset = services["maintenance_asset_service"].update_asset(
        asset.id,
        name="Updated Asset Alpha",
        service_level="TIER-1",
        expected_version=asset.version,
    )
    component = services["maintenance_asset_component_service"].create_component(
        asset_id=asset.id,
        component_code="bearing-upd",
        name="Bearing Assembly",
    )
    updated_component = services["maintenance_asset_component_service"].update_component(
        component.id,
        manufacturer_part_number="BRG-442",
        expected_life_cycles=250000,
        expected_version=component.version,
    )

    assert updated_location.name == "Workshop Alpha"
    assert updated_location.version == location.version + 1
    assert services["maintenance_location_service"].get_location(location.id).name == "Workshop Alpha"
    assert updated_asset.name == "Updated Asset Alpha"
    assert updated_asset.service_level == "TIER-1"
    assert updated_asset.version == asset.version + 1
    assert updated_component.manufacturer_part_number == "BRG-442"
    assert updated_component.expected_life_cycles == 250000
    assert updated_component.version == component.version + 1


def test_maintenance_system_service_rejects_cross_site_persistent_location_reference(services):
    first_site = services["site_service"].create_site(site_code="MNT-A", name="Plant A")
    second_site = services["site_service"].create_site(site_code="MNT-B", name="Plant B")
    location = services["maintenance_location_service"].create_location(
        site_id=first_site.id,
        location_code="line-a",
        name="Line A",
    )

    try:
        services["maintenance_system_service"].create_system(
            site_id=second_site.id,
            system_code="bad-system",
            name="Bad System",
            location_id=location.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_SYSTEM_SITE_MISMATCH"
    else:
        raise AssertionError("Expected maintenance system site mismatch validation error.")


def test_maintenance_asset_service_rejects_cross_site_persistent_system_reference(services):
    first_site = services["site_service"].create_site(site_code="MA-A", name="Plant A")
    second_site = services["site_service"].create_site(site_code="MA-B", name="Plant B")
    location_a = services["maintenance_location_service"].create_location(
        site_id=first_site.id,
        location_code="line-a",
        name="Line A",
    )
    location_b = services["maintenance_location_service"].create_location(
        site_id=second_site.id,
        location_code="line-b",
        name="Line B",
    )
    system_b = services["maintenance_system_service"].create_system(
        site_id=second_site.id,
        system_code="sys-b",
        name="System B",
        location_id=location_b.id,
    )

    try:
        services["maintenance_asset_service"].create_asset(
            site_id=first_site.id,
            location_id=location_a.id,
            asset_code="bad-cross-site",
            name="Bad Cross Site Asset",
            system_id=system_b.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_ASSET_SITE_MISMATCH"
    else:
        raise AssertionError("Expected maintenance asset site mismatch validation error.")


def test_maintenance_component_service_rejects_cross_asset_parent_reference(services):
    site = services["site_service"].create_site(site_code="MC-A", name="Plant C")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="area-c",
        name="Area C",
    )
    asset_a = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="asset-c1",
        name="Asset C1",
    )
    asset_b = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="asset-c2",
        name="Asset C2",
    )
    parent_component = services["maintenance_asset_component_service"].create_component(
        asset_id=asset_a.id,
        component_code="comp-parent",
        name="Parent Component",
    )

    try:
        services["maintenance_asset_component_service"].create_component(
            asset_id=asset_b.id,
            component_code="comp-child",
            name="Child Component",
            parent_component_id=parent_component.id,
        )
    except ValidationError as exc:
        assert exc.code == "MAINTENANCE_COMPONENT_ASSET_MISMATCH"
    else:
        raise AssertionError("Expected maintenance component asset mismatch validation error.")


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


def test_maintenance_integration_sources_persist_via_service_graph(services):
    source = services["maintenance_integration_source_service"].create_source(
        integration_code="erp-bridge-1",
        name="ERP Bridge 1",
        integration_type="ERP_BRIDGE",
        endpoint_or_path="https://erp.example.test/api/maintenance",
        authentication_mode="OAUTH2",
        schedule_expression="0 */4 * * *",
    )
    failed = services["maintenance_integration_source_service"].record_sync_failure(
        source.id,
        error_message="Unauthorized",
        expected_version=source.version,
    )
    recovered = services["maintenance_integration_source_service"].record_sync_success(
        source.id,
        expected_version=failed.version,
    )
    reloaded = services["maintenance_integration_source_service"].find_source_by_code("ERP-BRIDGE-1")
    listed = services["maintenance_integration_source_service"].list_sources(integration_type="ERP_BRIDGE")

    assert reloaded is not None
    assert reloaded.id == source.id
    assert reloaded.last_successful_sync_at is not None
    assert reloaded.last_error_message == ""
    assert recovered.version == failed.version + 1
    assert [row.id for row in listed] == [source.id]


def test_maintenance_sensor_mappings_and_exceptions_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-P4", name="Phase4 Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="p4-area",
        name="Phase4 Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="p4-asset",
        name="Phase4 Asset",
    )
    source = services["maintenance_integration_source_service"].create_source(
        integration_code="p4-source",
        name="Phase4 Source",
        integration_type="IOT_GATEWAY",
    )
    sensor = services["maintenance_sensor_service"].create_sensor(
        site_id=site.id,
        sensor_code="p4-sensor",
        sensor_name="Phase4 Sensor",
        asset_id=asset.id,
        sensor_type="TEMPERATURE",
        unit="C",
    )
    mapping = services["maintenance_sensor_source_mapping_service"].create_mapping(
        integration_source_id=source.id,
        sensor_id=sensor.id,
        external_equipment_key="EQ-P4",
        external_measurement_key="TEMP_P4",
    )
    services["maintenance_integration_source_service"].record_sync_failure(
        source.id,
        error_message="Gateway timeout",
        expected_version=source.version,
    )
    services["maintenance_sensor_reading_service"].record_reading(
        sensor_id=sensor.id,
        reading_value="77.5",
        reading_unit="C",
        quality_state="STALE",
        source_batch_id="BATCH-P4",
    )

    mappings = services["maintenance_sensor_source_mapping_service"].list_mappings(sensor_id=sensor.id)
    exceptions = services["maintenance_sensor_exception_service"].list_exceptions()

    assert [row.id for row in mappings] == [mapping.id]
    assert any(row.integration_source_id == source.id and row.exception_type.value == "EXTERNAL_SYNC_FAILURE" for row in exceptions)
    assert any(row.sensor_id == sensor.id and row.exception_type.value == "STALE_READING" for row in exceptions)


def test_maintenance_failure_codes_and_downtime_events_persist_via_service_graph(services):
    site = services["site_service"].create_site(site_code="MNT-RLY", name="Reliability Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="rly-area",
        name="Reliability Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="rly-asset",
        name="Reliability Asset",
    )
    symptom_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="seal-leak",
        name="Seal Leak",
        code_type="symptom",
    )
    cause_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="misalignment",
        name="Misalignment",
        code_type="cause",
    )
    work_request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-rly-100",
        source_type="manual",
        request_type="breakdown",
        asset_id=asset.id,
        location_id=location.id,
        title="Seal leak on main pump",
        failure_symptom_code=symptom_code.failure_code,
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-rly-100",
        work_order_type="corrective",
        source_type="work_request",
        source_id=work_request.id,
    )
    updated_work_order = services["maintenance_work_order_service"].update_work_order(
        work_order.id,
        failure_code=symptom_code.failure_code,
        root_cause_code=cause_code.failure_code,
        expected_version=work_order.version,
    )
    downtime_event = services["maintenance_downtime_event_service"].create_downtime_event(
        work_order_id=updated_work_order.id,
        started_at="2026-04-03T08:00:00+00:00",
        ended_at="2026-04-03T09:15:00+00:00",
        downtime_type="unplanned",
        reason_code=symptom_code.failure_code,
        impact_notes="Production stopped during seal replacement.",
    )

    listed_codes = services["maintenance_failure_code_service"].list_failure_codes()
    listed_events = services["maintenance_downtime_event_service"].list_downtime_events(
        work_order_id=updated_work_order.id
    )
    reloaded_work_order = services["maintenance_work_order_service"].get_work_order(updated_work_order.id)

    assert [row.failure_code for row in listed_codes] == ["MISALIGNMENT", "SEAL-LEAK"]
    assert [row.id for row in listed_events] == [downtime_event.id]
    assert listed_events[0].duration_minutes == 75
    assert reloaded_work_order.failure_code == symptom_code.failure_code
    assert reloaded_work_order.root_cause_code == cause_code.failure_code
    assert reloaded_work_order.downtime_minutes == 75


def test_maintenance_reliability_service_summarizes_persisted_patterns(services):
    site = services["site_service"].create_site(site_code="MNT-RPT", name="Reliability Reporting Plant")
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="rpt-area",
        name="Reporting Area",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        asset_code="rpt-asset",
        name="Reporting Asset",
    )
    symptom_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="bearing-hot",
        name="Bearing Hot",
        code_type="symptom",
    )
    cause_code = services["maintenance_failure_code_service"].create_failure_code(
        failure_code="lube-loss",
        name="Lubrication Loss",
        code_type="cause",
    )

    for index in range(1, 3):
        work_request = services["maintenance_work_request_service"].create_work_request(
            site_id=site.id,
            work_request_code=f"wr-rpt-{index}",
            source_type="manual",
            request_type="breakdown",
            asset_id=asset.id,
            location_id=location.id,
            title=f"Bearing issue {index}",
            failure_symptom_code=symptom_code.failure_code,
        )
        work_order = services["maintenance_work_order_service"].create_work_order(
            site_id=site.id,
            work_order_code=f"wo-rpt-{index}",
            work_order_type="corrective",
            source_type="work_request",
            source_id=work_request.id,
        )
        planned = services["maintenance_work_order_service"].update_work_order(
            work_order.id,
            status="planned",
            expected_version=work_order.version,
        )
        released = services["maintenance_work_order_service"].update_work_order(
            planned.id,
            status="released",
            expected_version=planned.version,
        )
        in_progress = services["maintenance_work_order_service"].update_work_order(
            work_order.id,
            status="in_progress",
            expected_version=released.version,
        )
        completed = services["maintenance_work_order_service"].update_work_order(
            in_progress.id,
            status="completed",
            failure_code=symptom_code.failure_code,
            root_cause_code=cause_code.failure_code,
            expected_version=in_progress.version,
        )
        services["maintenance_downtime_event_service"].create_downtime_event(
            work_order_id=completed.id,
            started_at="2026-04-03T08:00:00+00:00",
            ended_at="2026-04-03T09:00:00+00:00",
            downtime_type="unplanned",
            reason_code=symptom_code.failure_code,
            impact_notes="Bearing temperature forced shutdown.",
        )

    dashboard = services["maintenance_reliability_service"].build_reliability_dashboard(
        asset_id=asset.id,
        days=365,
    )
    recurring = services["maintenance_reliability_service"].list_recurring_failure_patterns(
        asset_id=asset.id,
        days=365,
        min_occurrences=2,
    )
    suggestions = services["maintenance_reliability_service"].suggest_root_causes(
        failure_code=symptom_code.failure_code,
        asset_id=asset.id,
    )

    summary = {metric.label: metric.value for metric in dashboard.summary}
    assert summary["Open work orders"] == 0
    assert summary["Downtime minutes"] == 120
    assert dashboard.top_root_causes[0].root_cause_code == cause_code.failure_code
    assert recurring[0].occurrence_count == 2
    assert recurring[0].leading_root_cause_code == cause_code.failure_code
    assert suggestions[0].root_cause_code == cause_code.failure_code
