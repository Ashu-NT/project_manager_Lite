"""Employee Detail's Activity tab -- canonical ActivityItemViewModel feed
wired end-to-end through the admin desktop API, mirroring Department's own
activity presenter (see test coverage patterns already established for
test_department_activity_presenter.py)."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_employee_activity_page_reports_distinct_lifecycle_actions(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="ACT-EMP-DEPT-1", name="Activity Dept")
    employee = employee_service.create_employee(
        employee_code="ACT-EMP-1", full_name="Activity Employee", department_id=department.id
    )
    employee_service.deactivate_employee(employee.id)
    employee_service.activate_employee(employee.id)

    page = admin.employeeActivityPage(employee.id, organization_id, 1, 25, "", "")
    actions_text = " ".join(item["title"] for item in page["items"])
    assert "reinstated" in actions_text.lower()
    assert "removed" in actions_text.lower()
    assert page["totalCount"] >= 3
    assert page["filteredTotal"] >= 3

    recent = admin.employeeActivity(employee.id, organization_id)
    assert len(recent) >= 1


def test_employee_activity_page_true_empty_state_before_any_activity(services) -> None:
    """A brand-new employee already has an employee.create activity entry --
    this asserts the search-filtered (not true-empty) path instead, matching
    the presenter's noResultsState wording."""
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="ACT-EMP-DEPT-2", name="Activity Dept Two")
    employee = employee_service.create_employee(
        employee_code="ACT-EMP-2", full_name="Activity Employee Two", department_id=department.id
    )

    page = admin.employeeActivityPage(employee.id, organization_id, 1, 25, "no-such-activity-search", "")
    assert page["filteredTotal"] == 0
    assert page["totalCount"] >= 1
    assert "No activity matches your current filters." == page["noResultsState"]
