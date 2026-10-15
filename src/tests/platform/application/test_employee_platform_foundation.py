from __future__ import annotations

from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.application.master_data.site.dto.commands.site import (
    SiteCreateCommand,
)


def test_employee_profile_remains_platform_owned_and_pm_reads_live_identity(services):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code="LAG", name="Lagos HQ"))
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="PMO", name="PMO", site_id=site.id))

    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EMP-001", full_name="Alice Admin", department_id=department.id, department="PMO", site_id=site.id, site_name="Lagos HQ", title="Planner", email="alice@example.com"))

    resource = services["resource_master_commands"].create_resource(
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

    next_site = services["site_commands"].create_site(SiteCreateCommand(site_code="BER", name="Berlin Hub"))
    next_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="PLN", name="Planning", site_id=next_site.id))

    employee = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Alice Smith", department_id=next_department.id, site_name="Berlin Hub", site_id=next_site.id, title="Senior Planner", email="", phone="+49-555-0101", expected_version=employee.version))

    refreshed = services["resource_query"].get_resource(resource.id)
    summary = services["resource_query"].get_resource_summary(resource.id)
    catalog = services["resource_query"].query_catalog_page(search_text="Alice Smith")

    assert employee.site_name == "Berlin Hub"
    assert employee.site_id == next_site.id
    assert employee.department == "Planning"
    assert employee.department_id == next_department.id
    assert refreshed.version == resource.version
    assert refreshed.name == "Alice Admin"  # PM-owned registration is not rewritten by Platform.
    assert refreshed.role == "Planner"
    assert summary.name == "Alice Smith"
    assert summary.employee_title == "Senior Planner"
    assert summary.contact == "+49-555-0101"
    assert summary.department_id == next_department.id
    assert summary.site_id == next_site.id
    assert [item.resource_id for item in catalog.items] == [resource.id]


