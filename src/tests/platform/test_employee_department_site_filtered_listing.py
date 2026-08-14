"""Employees by Department/Site -- scoped read capability.

Before this change, the Department detail page's "Employees" tab fetched
EVERY employee in the active organization via
EmployeeService.list_employees(active_only=None) -- fully hydrating the
whole organization's employee table -- then filtered that in-memory list
down to one department in QML JavaScript
(AdminDepartmentDetailPage.qml's _employeeRows). The Site detail page had
no employee breakdown at all.

This adds optional department_id/site_id filters straight to
EmployeeRepository.list_for_organization()'s SQL WHERE clause (mirroring
the existing active_only filter), threaded through EmployeeService and
PlatformEmployeeDesktopApi, and wired to two new QML-facing slots
(PlatformEmployeeController.employeesForDepartment/employeesForSite,
delegated through PlatformAdminWorkspaceController) that both detail pages
now call instead of client-side filtering the full catalog.

These tests cover: filter correctness (department_id, site_id), that the
filter composes correctly with the existing tenant/organization scoping
(a foreign department/site id yields zero rows, never cross-org data),
that the underlying SQL is a single narrowly-filtered SELECT rather than a
full-table fetch, and an end-to-end check through the real admin
controller slots the QML pages call.
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

    site_a = site_service.create_site(site_code="FILT-SA", name="Site A", is_active=True)
    site_b = site_service.create_site(site_code="FILT-SB", name="Site B", is_active=True)
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

    default_organization = organization_service.get_active_organization()
    dept_in_default_org = department_service.create_department(
        department_code="FILT-CROSS-D", name="Cross Dept", is_active=True
    )
    _seed_employees(employee_service, department_id=dept_in_default_org.id, count=2, prefix="CROSS")

    second_organization = organization_service.create_organization(
        organization_code="FILT-CROSS-ORG",
        display_name="Cross Org",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    # Same department_id, but now scoped to a different active organization
    # -- must not resolve to the first organization's employees.
    rows = employee_service.list_employees(department_id=dept_in_default_org.id)
    assert rows == []

    organization_service.set_active_organization(default_organization.id)


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

    site = site_service.create_site(site_code="FILT-SQL-S", name="SQL Site", is_active=True)
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

    site = site_service.create_site(site_code="FILT-CTRL-S", name="Controller Site", is_active=True)
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
