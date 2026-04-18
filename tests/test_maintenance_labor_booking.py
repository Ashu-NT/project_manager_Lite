from __future__ import annotations

from datetime import date

import pytest

from src.core.platform.common.exceptions import ValidationError


def _create_labor_context(services):
    site = services["site_service"].create_site(
        site_code="MNT-LAB",
        name="Maintenance Labor Site",
        currency_code="EUR",
    )
    location = services["maintenance_location_service"].create_location(
        site_id=site.id,
        location_code="labor-area",
        name="Labor Area",
    )
    system = services["maintenance_system_service"].create_system(
        site_id=site.id,
        location_id=location.id,
        system_code="labor-system",
        name="Labor System",
    )
    asset = services["maintenance_asset_service"].create_asset(
        site_id=site.id,
        location_id=location.id,
        system_id=system.id,
        asset_code="labor-asset",
        name="Labor Asset",
    )
    employee = services["employee_service"].create_employee(
        employee_code="mnt-labor-01",
        full_name="Maintenance Labor Technician",
        site_id=site.id,
        site_name=site.name,
        department="Maintenance",
        title="Technician",
    )
    request = services["maintenance_work_request_service"].create_work_request(
        site_id=site.id,
        work_request_code="wr-labor-01",
        source_type="manual",
        request_type="corrective",
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Labor booking request",
    )
    work_order = services["maintenance_work_order_service"].create_work_order(
        site_id=site.id,
        work_order_code="wo-labor-01",
        work_order_type="corrective",
        source_type="work_request",
        source_id=request.id,
        asset_id=asset.id,
        location_id=location.id,
        system_id=system.id,
        title="Labor booking work order",
    )
    assigned_task = services["maintenance_work_order_task_service"].create_task(
        work_order_id=work_order.id,
        task_name="Inspect pump alignment",
        assigned_employee_id=employee.id,
        estimated_minutes=90,
        required_skill="Mechanical",
    )
    unassigned_task = services["maintenance_work_order_task_service"].create_task(
        work_order_id=work_order.id,
        task_name="Review follow-up findings",
        estimated_minutes=30,
    )
    return asset, employee, assigned_task, unassigned_task


def test_maintenance_labor_service_books_shared_time_against_work_order_tasks(services):
    asset, employee, assigned_task, _unassigned_task = _create_labor_context(services)

    entry = services["maintenance_labor_service"].add_task_labor_entry(
        work_order_task_id=assigned_task.id,
        entry_date=date(2026, 4, 4),
        hours=2.5,
        note="Seal alignment and vibration check.",
    )

    entries = services["maintenance_labor_service"].list_task_labor_entries(assigned_task.id)
    refreshed_task = services["maintenance_work_order_task_service"].get_task(assigned_task.id)

    assert entry.work_allocation_id == assigned_task.id
    assert entry.owner_type == "maintenance_work_order_task"
    assert entry.owner_id == assigned_task.id
    assert entry.scope_type == "maintenance"
    assert entry.scope_id == asset.id
    assert entry.employee_id == employee.id
    assert entry.department_name == "Maintenance"
    assert entry.site_name == "Maintenance Labor Site"
    assert len(entries) == 1
    assert entries[0].hours == pytest.approx(2.5)
    assert refreshed_task.actual_minutes == 150


def test_maintenance_labor_service_requires_assigned_employee_for_booking(services):
    _asset, _employee, _assigned_task, unassigned_task = _create_labor_context(services)

    with pytest.raises(ValidationError, match="Assign an employee"):
        services["maintenance_labor_service"].add_task_labor_entry(
            work_order_task_id=unassigned_task.id,
            entry_date=date(2026, 4, 4),
            hours=1.0,
            note="Should fail without an assigned technician.",
        )
