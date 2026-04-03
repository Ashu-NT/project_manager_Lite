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

    assert reloaded_work_request is not None
    assert reloaded_work_request.id == work_request.id
    assert reloaded_work_request.source_type.value == "MANUAL"
    assert reloaded_work_request.request_type == "BREAKDOWN"
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
