from __future__ import annotations

from src.core.modules.project_management.domain.enums import WorkerType


def test_employee_updates_keep_linked_resources_in_sync(services):
    employee_service = services["employee_service"]
    resource_service = services["resource_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    site = site_service.create_site(site_code="LAG", name="Lagos HQ")
    department = department_service.create_department(
        department_code="PMO",
        name="PMO",
        site_id=site.id,
    )

    employee = employee_service.create_employee(
        employee_code="EMP-001",
        full_name="Alice Admin",
        department_id=department.id,
        department="PMO",
        site_id=site.id,
        site_name="Lagos HQ",
        title="Planner",
        email="alice@example.com",
    )

    resource = resource_service.create_resource(
        "",
        hourly_rate=125.0,
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )

    assert resource.worker_type == WorkerType.EMPLOYEE
    assert resource.employee_id == employee.id
    assert employee.department_id == department.id
    assert employee.site_id == site.id
    assert resource.name == "Alice Admin"
    assert resource.role == "Planner"
    assert resource.contact == "alice@example.com"

    next_site = site_service.create_site(site_code="BER", name="Berlin Hub")
    next_department = department_service.create_department(
        department_code="PLN",
        name="Planning",
        site_id=next_site.id,
    )

    employee = employee_service.update_employee(
        employee.id,
        full_name="Alice Smith",
        department_id=next_department.id,
        site_name="Berlin Hub",
        site_id=next_site.id,
        title="Senior Planner",
        email="",
        phone="+49-555-0101",
        expected_version=employee.version,
    )

    refreshed = resource_service.get_resource(resource.id)

    assert employee.site_name == "Berlin Hub"
    assert employee.site_id == next_site.id
    assert employee.department == "Planning"
    assert employee.department_id == next_department.id
    assert refreshed.name == "Alice Smith"
    assert refreshed.role == "Senior Planner"
    assert refreshed.contact == "+49-555-0101"

