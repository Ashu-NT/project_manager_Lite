"""Department Detail's own paginated Employees tab -- server-side search,
status filtering, and pagination scoped to department_id, mirroring
employeesForSitePage(). Also guards the department_id equivalent of the
total-count bug fixed for site_id in list_page_for_organization_in_tenant:
the unfiltered total must reflect only this department's employees, not
the whole organization's."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_employees_for_department_page_total_excludes_other_departments(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department_a = department_service.create_department(department_code="EFDP-A", name="Dept A")
    department_b = department_service.create_department(department_code="EFDP-B", name="Dept B")
    employee_service.create_employee(employee_code="EFDP-E1", full_name="In Dept A", department_id=department_a.id)
    employee_service.create_employee(employee_code="EFDP-E2", full_name="Also In Dept A", department_id=department_a.id)
    employee_service.create_employee(employee_code="EFDP-E3", full_name="In Dept B", department_id=department_b.id)

    page = admin.employeesForDepartmentPage(department_a.id, organization_id, 1, 25, "", "")
    names = [item["title"] for item in page["items"]]
    assert sorted(names) == ["Also In Dept A", "In Dept A"]
    # Both the unfiltered total AND the filtered total must be scoped to
    # this department -- not leak department B's (or the whole
    # organization's) employee count.
    assert page["totalCount"] == 2
    assert page["filteredTotal"] == 2


def test_employees_for_department_page_search_and_status_filter(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="EFDP-C", name="Dept C")
    active_employee = employee_service.create_employee(
        employee_code="EFDP-E4", full_name="Findme Active", department_id=department.id
    )
    inactive_employee = employee_service.create_employee(
        employee_code="EFDP-E5", full_name="Someone Else", department_id=department.id
    )
    employee_service.deactivate_employee(inactive_employee.id)

    search_page = admin.employeesForDepartmentPage(department.id, organization_id, 1, 25, "Findme", "")
    assert [item["title"] for item in search_page["items"]] == ["Findme Active"]
    assert search_page["totalCount"] == 2
    assert search_page["filteredTotal"] == 1

    active_page = admin.employeesForDepartmentPage(department.id, organization_id, 1, 25, "", "active")
    assert [item["title"] for item in active_page["items"]] == ["Findme Active"]

    inactive_page = admin.employeesForDepartmentPage(department.id, organization_id, 1, 25, "", "inactive")
    assert [item["title"] for item in inactive_page["items"]] == ["Someone Else"]


def test_employees_for_department_page_true_empty_state(services) -> None:
    department_service = services["department_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="EFDP-D", name="Dept D")
    page = admin.employeesForDepartmentPage(department.id, organization_id, 1, 25, "", "")
    assert page["items"] == []
    assert page["totalCount"] == 0
    assert page["filteredTotal"] == 0
    assert page["emptyState"] == "No employees assigned to this department."
