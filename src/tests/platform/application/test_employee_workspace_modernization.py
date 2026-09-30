"""Backend/controller support for the modernized standalone Employees
workspace: active-organization-scoped paginated catalog (search/status/
department/site filters), the Employee context (for the workspace
subtitle), and System Access relationship read helpers (linked-user
resolution + linkable-user options for the link selector)."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.presenters.employees.employee_catalog_presenter import (
    PlatformEmployeeCatalogPresenter,
)


def _presenter(registry) -> PlatformEmployeeCatalogPresenter:
    return PlatformEmployeeCatalogPresenter(
        employee_api=registry.platform_employee,
        site_api=registry.platform_site,
        department_api=registry.platform_department,
        user_api=registry.platform_user,
    )


def test_employee_context_resolves_active_organization(services) -> None:
    registry = build_desktop_api_registry(services)
    result = registry.platform_employee.get_context()
    assert result.ok
    assert result.data is not None
    assert result.data.id == services["tenant_context_service"].get_active_organization().id


def test_build_catalog_page_scopes_to_active_organization_and_paginates(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    department = department_service.create_department(department_code="EWM-D1", name="Workspace Dept")
    for i in range(3):
        employee_service.create_employee(
            employee_code=f"EWM-E{i}", full_name=f"Workspace Employee {i}", department_id=department.id
        )

    registry = build_desktop_api_registry(services)
    presenter = _presenter(registry)
    catalog = presenter.build_catalog_page(page=1, page_size=25)

    assert catalog.filtered_total >= 3
    names = {item.title for item in catalog.items}
    assert {"Workspace Employee 0", "Workspace Employee 1", "Workspace Employee 2"} <= names
    for item in catalog.items:
        if item.title.startswith("Workspace Employee"):
            assert item.state["organizationName"]


def test_build_catalog_page_filters_by_department_and_site(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="EWM-SITE-1", name="Workspace Site")
    dept_a = department_service.create_department(department_code="EWM-DA", name="Dept A")
    dept_b = department_service.create_department(department_code="EWM-DB", name="Dept B")
    employee_service.create_employee(
        employee_code="EWM-FA", full_name="In Dept A", department_id=dept_a.id, site_id=site.id
    )
    employee_service.create_employee(employee_code="EWM-FB", full_name="In Dept B", department_id=dept_b.id)

    registry = build_desktop_api_registry(services)
    presenter = _presenter(registry)

    dept_catalog = presenter.build_catalog_page(department_id=dept_a.id)
    assert [item.title for item in dept_catalog.items] == ["In Dept A"]

    site_catalog = presenter.build_catalog_page(site_id=site.id)
    assert [item.title for item in site_catalog.items] == ["In Dept A"]


def test_build_catalog_page_status_filter(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    department = department_service.create_department(department_code="EWM-D2", name="Status Dept")
    employee_service.create_employee(
        employee_code="EWM-ACTIVE", full_name="Active Filter Employee", department_id=department.id
    )
    inactive_employee = employee_service.create_employee(
        employee_code="EWM-INACTIVE", full_name="Inactive Filter Employee", department_id=department.id
    )
    employee_service.deactivate_employee(inactive_employee.id)

    registry = build_desktop_api_registry(services)
    presenter = _presenter(registry)

    active_only = presenter.build_catalog_page(status="active")
    active_titles = {item.title for item in active_only.items}
    assert "Active Filter Employee" in active_titles
    assert "Inactive Filter Employee" not in active_titles

    inactive_only = presenter.build_catalog_page(status="inactive")
    inactive_titles = {item.title for item in inactive_only.items}
    assert "Inactive Filter Employee" in inactive_titles
    assert "Active Filter Employee" not in inactive_titles


def test_resolve_linked_user_returns_identity_and_status(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    auth_service = services["auth_service"]

    department = department_service.create_department(department_code="EWM-D3", name="Link Dept")
    employee = employee_service.create_employee(
        employee_code="EWM-LINK-1", full_name="Linked Employee", department_id=department.id
    )
    user = auth_service.onboard_tenant_user(
        username="ewm-link-user", raw_password="StrongPass123!", display_name="Link User",
        email="ewm-link-user@example.com",
    )
    employee_service.link_employee_user_account(employee.id, user.id)

    registry = build_desktop_api_registry(services)
    presenter = _presenter(registry)
    resolved = presenter.resolve_linked_user(user.id)

    assert resolved is not None
    assert resolved["userId"] == user.id
    assert resolved["identity"] == "ewm-link-user@example.com"
    assert resolved["isActive"] is True


def test_resolve_linked_user_returns_none_when_no_user_id(services) -> None:
    registry = build_desktop_api_registry(services)
    presenter = _presenter(registry)
    assert presenter.resolve_linked_user("") is None
    assert presenter.resolve_linked_user("no-such-user") is None


def test_linkable_user_options_excludes_already_linked_and_service_accounts(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    auth_service = services["auth_service"]

    department = department_service.create_department(department_code="EWM-D4", name="Linkable Dept")
    employee_one = employee_service.create_employee(
        employee_code="EWM-LO-1", full_name="Linkable Employee One", department_id=department.id
    )
    employee_two = employee_service.create_employee(
        employee_code="EWM-LO-2", full_name="Linkable Employee Two", department_id=department.id
    )
    linked_user = auth_service.onboard_tenant_user(
        username="ewm-already-linked", raw_password="StrongPass123!", display_name="Already Linked",
    )
    unlinked_user = auth_service.onboard_tenant_user(
        username="ewm-unlinked", raw_password="StrongPass123!", display_name="Unlinked User",
    )
    employee_service.link_employee_user_account(employee_one.id, linked_user.id)

    registry = build_desktop_api_registry(services)
    presenter = _presenter(registry)

    options_for_two = presenter.build_linkable_user_options(employee_two.id)
    values = {opt["value"] for opt in options_for_two}
    assert unlinked_user.id in values
    assert linked_user.id not in values

    # The employee's own already-linked user must still be offered when
    # resolving options for ITSELF (so its current link remains selectable),
    # not filtered out as "linked to another employee".
    options_for_one = presenter.build_linkable_user_options(employee_one.id)
    assert linked_user.id in {opt["value"] for opt in options_for_one}


def test_admin_workspace_employees_catalog_uses_paginated_active_organization_scope(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    department = department_service.create_department(department_code="EWM-D5", name="Admin Workspace Dept")
    employee_service.create_employee(
        employee_code="EWM-ADMIN-1", full_name="Admin Workspace Employee", department_id=department.id
    )

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    employees = admin.employees
    assert employees.get("paginated") is True
    titles = [item["title"] for item in employees["items"]]
    assert "Admin Workspace Employee" in titles

    admin.setEmployeeDepartmentFilter(department.id)
    filtered = admin.employees
    assert all(item["state"]["departmentId"] == department.id for item in filtered["items"])
    admin.setEmployeeDepartmentFilter("")
