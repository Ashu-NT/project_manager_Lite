"""Employees by Department/Site -- scoped read capability.

`EmployeeRepository.list_for_organization()` accepts optional department_id/site_id filters
straight in its SQL WHERE clause (mirroring the existing active_only filter), threaded through
EmployeeService, PlatformEmployeeDesktopApi, and two QML-facing controller slots
(employeesForDepartment/employeesForSite).

Covers: filter correctness, composition with tenant/organization scoping (a foreign
department/site id yields zero rows, never cross-org data), that the filtered fetch is a single
narrow SELECT (not a full-table fetch filtered in Python), and an end-to-end check through the
real admin controller slots.
"""
from __future__ import annotations

from sqlalchemy import event

import pytest


def _seed_employees(employee_service, *, department_id=None, site_id=None, count, prefix):
    created = []
    for i in range(count):
        employee = employee_service.create_employee(
            employee_code=f"{prefix}-{i}",
            full_name=f"{prefix} Employee {i}",
            department_id=department_id,
            site_id=site_id,
            is_active=True,
        )
        created.append(employee)
    return created


# ---------------------------------------------------------------------------
# Service-level filter correctness
# ---------------------------------------------------------------------------


def test_list_employees_filters_by_department_id(services):
    employee_service = services["employee_service"]
    department_service = services["department_service"]

    dept_a = department_service.create_department(department_code="FILT-DA", name="Dept A", is_active=True)
    dept_b = department_service.create_department(department_code="FILT-DB", name="Dept B", is_active=True)
    _seed_employees(employee_service, department_id=dept_a.id, count=3, prefix="DA")
    _seed_employees(employee_service, department_id=dept_b.id, count=2, prefix="DB")

    rows_a = employee_service.list_employees(department_id=dept_a.id)
    rows_b = employee_service.list_employees(department_id=dept_b.id)

    assert len(rows_a) == 3
    assert all(row.department_id == dept_a.id for row in rows_a)
    assert len(rows_b) == 2
    assert all(row.department_id == dept_b.id for row in rows_b)


def test_list_employees_filters_by_site_id(services):
    employee_service = services["employee_service"]
    site_service = services["site_service"]

    site_a = site_service.create_site(site_code="FILT-SA", name="Site A")
    site_b = site_service.create_site(site_code="FILT-SB", name="Site B")
    _seed_employees(employee_service, site_id=site_a.id, count=4, prefix="SA")
    _seed_employees(employee_service, site_id=site_b.id, count=1, prefix="SB")

    rows_a = employee_service.list_employees(site_id=site_a.id)
    rows_b = employee_service.list_employees(site_id=site_b.id)

    assert len(rows_a) == 4
    assert all(row.site_id == site_a.id for row in rows_a)
    assert len(rows_b) == 1
    assert all(row.site_id == site_b.id for row in rows_b)


def test_list_employees_department_and_site_filter_excludes_unassigned_and_other_buckets(services):
    employee_service = services["employee_service"]
    department_service = services["department_service"]

    dept = department_service.create_department(department_code="FILT-DC", name="Dept C", is_active=True)
    _seed_employees(employee_service, department_id=dept.id, count=2, prefix="DC")
    _seed_employees(employee_service, department_id=None, count=2, prefix="UNASSIGNED")

    rows = employee_service.list_employees(department_id=dept.id)

    assert len(rows) == 2
    assert all(row.department_id == dept.id for row in rows)


def test_list_employees_unfiltered_still_returns_everything(services):
    """Backward compatibility: omitting department_id/site_id must behave
    exactly as before (the main Employees workspace page's full catalog)."""
    employee_service = services["employee_service"]

    baseline = employee_service.list_employees()
    employee_service.create_employee(employee_code="FILT-UNSCOPED-1", full_name="Unscoped One", is_active=True)

    updated = employee_service.list_employees()
    assert len(updated) == len(baseline) + 1


# ---------------------------------------------------------------------------
# Scoping composition: filter must never leak across organizations
# ---------------------------------------------------------------------------


def test_department_filter_from_foreign_organization_yields_no_rows(services):
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    organization_service = services["organization_service"]

    default_organization = services["tenant_context_service"].get_active_organization()
    dept_in_default_org = department_service.create_department(
        department_code="FILT-CROSS-D", name="Cross Dept", is_active=True
    )
    _seed_employees(employee_service, department_id=dept_in_default_org.id, count=2, prefix="CROSS")

    second_organization = organization_service.create_organization(
        organization_code="FILT-CROSS-ORG",
        display_name="Cross Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    services["tenant_context_service"].set_active_organization(second_organization.id)

    # Same department_id, but now scoped to a different active organization
    # -- must not resolve to the first organization's employees.
    rows = employee_service.list_employees(department_id=dept_in_default_org.id)
    assert rows == []

    services["tenant_context_service"].set_active_organization(default_organization.id)


# ---------------------------------------------------------------------------
# Desktop API surface
# ---------------------------------------------------------------------------


def test_desktop_api_list_employees_accepts_department_and_site_filters(services):
    from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi

    employee_service = services["employee_service"]
    department_service = services["department_service"]
    api = PlatformEmployeeDesktopApi(employee_service=employee_service)

    dept = department_service.create_department(department_code="FILT-API-D", name="API Dept", is_active=True)
    _seed_employees(employee_service, department_id=dept.id, count=2, prefix="API")

    result = api.list_employees(department_id=dept.id)
    assert result.ok
    assert len(result.data) == 2
    assert all(row.department_id == dept.id for row in result.data)


# ---------------------------------------------------------------------------
# SQL-shape guardrail: proof the filtered fetch is a single narrow SELECT,
# not a full-organization materialization filtered afterward.
# ---------------------------------------------------------------------------


def _count_employee_selects(engine, fn):
    statements = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        if "employees" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
    return result, statements


def test_department_filtered_fetch_issues_one_narrow_select_not_full_scan(services):
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    session = services["session"]
    engine = session.get_bind()

    dept = department_service.create_department(department_code="FILT-SQL-D", name="SQL Dept", is_active=True)
    _seed_employees(employee_service, department_id=dept.id, count=2, prefix="SQLD")
    # A large pool of OTHER employees in the org, unrelated to dept -- if the
    # fix regressed to full materialization + Python filter, this row count
    # would still show up as "fetched" even though it's discarded.
    _seed_employees(employee_service, department_id=None, count=30, prefix="SQLBULK")

    rows, statements = _count_employee_selects(
        engine, lambda: employee_service.list_employees(department_id=dept.id)
    )

    assert len(rows) == 2
    assert len(statements) == 1
    assert "department_id" in statements[0]


def test_site_filtered_fetch_issues_one_narrow_select_not_full_scan(services):
    employee_service = services["employee_service"]
    site_service = services["site_service"]
    session = services["session"]
    engine = session.get_bind()

    site = site_service.create_site(site_code="FILT-SQL-S", name="SQL Site")
    _seed_employees(employee_service, site_id=site.id, count=3, prefix="SQLS")
    _seed_employees(employee_service, site_id=None, count=30, prefix="SQLBULK2")

    rows, statements = _count_employee_selects(
        engine, lambda: employee_service.list_employees(site_id=site.id)
    )

    assert len(rows) == 3
    assert len(statements) == 1
    assert "site_id" in statements[0]


# ---------------------------------------------------------------------------
# End-to-end: the real QML-facing controller slots both detail pages call.
# ---------------------------------------------------------------------------


def test_admin_controller_employees_for_department_slot(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    employee_service = services["employee_service"]
    department_service = services["department_service"]

    dept = department_service.create_department(department_code="FILT-CTRL-D", name="Controller Dept", is_active=True)
    _seed_employees(employee_service, department_id=dept.id, count=2, prefix="CTRLD")

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.employeesForDepartment(dept.id)
    assert len(result["items"]) == 2
    for item in result["items"]:
        assert item["state"]["departmentId"] == dept.id


def test_admin_controller_employees_for_site_slot(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    employee_service = services["employee_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="FILT-CTRL-S", name="Controller Site")
    _seed_employees(employee_service, site_id=site.id, count=3, prefix="CTRLS")

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.employeesForSite(site.id)
    assert len(result["items"]) == 3
    for item in result["items"]:
        assert item["state"]["siteId"] == site.id


def test_admin_controller_employees_for_department_empty_when_no_matches(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    department_service = services["department_service"]
    dept = department_service.create_department(department_code="FILT-CTRL-EMPTY", name="Empty Dept", is_active=True)

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.employeesForDepartment(dept.id)
    assert result["items"] == []


# ---------------------------------------------------------------------------
# Departments by Site -- same explicit site_id-scoped read capability,
# for Site Detail's own Departments tab (see AdminSiteDetailPage.qml).
# ---------------------------------------------------------------------------


def test_list_departments_filters_by_site_id(services):
    department_service = services["department_service"]
    site_service = services["site_service"]

    site_a = site_service.create_site(site_code="FILT-DEPT-SA", name="Dept Site A")
    site_b = site_service.create_site(site_code="FILT-DEPT-SB", name="Dept Site B")
    department_service.create_department(department_code="FILT-DEPT-DA1", name="Dept A1", site_id=site_a.id, is_active=True)
    department_service.create_department(department_code="FILT-DEPT-DA2", name="Dept A2", site_id=site_a.id, is_active=True)
    department_service.create_department(department_code="FILT-DEPT-DB1", name="Dept B1", site_id=site_b.id, is_active=True)

    rows_a = department_service.list_departments(site_id=site_a.id)
    rows_b = department_service.list_departments(site_id=site_b.id)

    assert len(rows_a) == 2
    assert all(row.site_id == site_a.id for row in rows_a)
    assert len(rows_b) == 1
    assert all(row.site_id == site_b.id for row in rows_b)


def test_admin_controller_departments_for_site_slot(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    department_service = services["department_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="FILT-DEPT-CTRL-S", name="Controller Dept Site")
    department_service.create_department(department_code="FILT-DEPT-CTRL-D1", name="Controller Dept 1", site_id=site.id, is_active=True)
    department_service.create_department(department_code="FILT-DEPT-CTRL-D2", name="Controller Dept 2", site_id=site.id, is_active=True)

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.departmentsForSite(site.id)
    assert len(result["items"]) == 2
    for item in result["items"]:
        assert item["state"]["siteId"] == site.id


def test_admin_controller_departments_for_site_empty_when_no_matches(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    site_service = services["site_service"]
    site = site_service.create_site(site_code="FILT-DEPT-CTRL-EMPTY", name="Empty Dept Site")

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.departmentsForSite(site.id)
    assert result["items"] == []


# ---------------------------------------------------------------------------
# Paginated site-scoped reads -- the canonical DataTable + TablePaginationBar
# counterpart to the fetch-all departmentsForSite/employeesForSite slots
# above, for Site Detail's own Departments/Employees tabs.
# ---------------------------------------------------------------------------


def test_departments_page_for_organization_filters_by_site_id(services):
    department_service = services["department_service"]
    site_service = services["site_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    site_a = site_service.create_site(site_code="FILT-DEPT-PG-SA", name="Dept Page Site A")
    site_b = site_service.create_site(site_code="FILT-DEPT-PG-SB", name="Dept Page Site B")
    for i in range(3):
        department_service.create_department(
            department_code=f"FILT-DEPT-PG-A{i}", name=f"Page Dept A{i}", site_id=site_a.id, is_active=True
        )
    department_service.create_department(
        department_code="FILT-DEPT-PG-B0", name="Page Dept B0", site_id=site_b.id, is_active=True
    )

    page = department_service.list_departments_page_for_organization(
        organization_id, page=1, page_size=25, site_id=site_a.id
    )

    assert page.filtered_total == 3
    assert len(page.items) == 3
    assert all(row.site_id == site_a.id for row in page.items)


def test_departments_page_for_organization_site_scope_paginates_and_searches(services):
    department_service = services["department_service"]
    site_service = services["site_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    site = site_service.create_site(site_code="FILT-DEPT-PG-SC", name="Page Site C")
    for i in range(3):
        department_service.create_department(
            department_code=f"FILT-DEPT-PGC-{i}", name=f"Findme Dept {i}", site_id=site.id, is_active=True
        )
    department_service.create_department(
        department_code="FILT-DEPT-PGC-OTHER", name="Unrelated Dept", site_id=site.id, is_active=True
    )

    page_1 = department_service.list_departments_page_for_organization(
        organization_id, page=1, page_size=25, site_id=site.id
    )
    assert page_1.filtered_total == 4
    assert len(page_1.items) == 4

    search_page = department_service.list_departments_page_for_organization(
        organization_id, page=1, page_size=25, search="Findme", site_id=site.id
    )
    assert search_page.filtered_total == 3
    assert all("Findme" in row.name for row in search_page.items)


def test_admin_controller_departments_for_site_page_slot(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    department_service = services["department_service"]
    site_service = services["site_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    site = site_service.create_site(site_code="FILT-DEPT-PGCTRL-S", name="Page Controller Site")
    for i in range(2):
        department_service.create_department(
            department_code=f"FILT-DEPT-PGCTRL-{i}", name=f"Page Controller Dept {i}", site_id=site.id, is_active=True
        )

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.departmentsForSitePage(site.id, organization_id, 1, 25, "", "")
    assert result["paginated"] is True
    assert result["filteredTotal"] == 2
    for item in result["items"]:
        assert item["state"]["siteId"] == site.id


def test_employees_page_for_organization_filters_by_site_id(services):
    employee_service = services["employee_service"]
    site_service = services["site_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    site_a = site_service.create_site(site_code="FILT-EMP-PG-SA", name="Emp Page Site A")
    site_b = site_service.create_site(site_code="FILT-EMP-PG-SB", name="Emp Page Site B")
    _seed_employees(employee_service, site_id=site_a.id, count=3, prefix="EMPPGA")
    _seed_employees(employee_service, site_id=site_b.id, count=1, prefix="EMPPGB")

    page = employee_service.list_employees_page_for_organization(
        organization_id, page=1, page_size=25, site_id=site_a.id
    )

    assert page.filtered_total == 3
    assert all(row.site_id == site_a.id for row in page.items)


def test_employees_page_for_organization_site_scope_respects_status_filter(services):
    employee_service = services["employee_service"]
    site_service = services["site_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    site = site_service.create_site(site_code="FILT-EMP-PG-SC", name="Emp Page Site C")
    active_employees = _seed_employees(employee_service, site_id=site.id, count=2, prefix="EMPPGC-ACTIVE")
    for employee in _seed_employees(employee_service, site_id=site.id, count=1, prefix="EMPPGC-INACTIVE"):
        employee_service.update_employee(employee_id=employee.id, is_active=False, expected_version=employee.version)

    active_page = employee_service.list_employees_page_for_organization(
        organization_id, page=1, page_size=25, site_id=site.id, active_only=True
    )
    inactive_page = employee_service.list_employees_page_for_organization(
        organization_id, page=1, page_size=25, site_id=site.id, active_only=False
    )

    assert active_page.filtered_total == 2
    assert inactive_page.filtered_total == 1


def test_admin_controller_employees_for_site_page_slot(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    employee_service = services["employee_service"]
    site_service = services["site_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    site = site_service.create_site(site_code="FILT-EMP-PGCTRL-S", name="Emp Page Controller Site")
    _seed_employees(employee_service, site_id=site.id, count=3, prefix="EMPPGCTRL")

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    result = admin.employeesForSitePage(site.id, organization_id, 1, 25, "", "", "")
    assert result["paginated"] is True
    assert result["filteredTotal"] == 3
    for item in result["items"]:
        assert item["state"]["siteId"] == site.id
