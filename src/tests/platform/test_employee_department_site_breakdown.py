"""Employees by Department/Site -- Overview breakdown analytics.

This is the deliberately separate analytics/read-model phase flagged when
the department/site-filtered employee listing (P6.5-style drill-down for
the Department/Site detail pages) was built: a GROUP BY aggregate across
ALL departments/sites at once, powering the Platform Overview's "Employees
by Department"/"Employees by Site" cards -- which previously showed a
hardcoded "Not yet available" placeholder.

Extends the existing EmployeeHeadcountReader (P6) rather than introducing a
new reader class, per the established precedent: employee-specific
aggregate reads live there. Employees with no department/site assigned are
bucketed under a ``None`` id labeled "Unassigned" rather than dropped,
since that's a real, expected state (Employee.department_id/site_id are
nullable).

These tests mirror test_employee_headcount_reader.py's structure:
reader-level unit tests (query count, unassigned bucket, ordering,
tenant/org isolation, isolated db), then service/desktop-API-level tests
through the real `services` fixture, then an end-to-end guardrail through
the real admin overview presenter.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.infra.persistence.orm import Base


# ---------------------------------------------------------------------------
# Reader-level unit tests: exact query count, unassigned bucket, ordering,
# tenant/organization scoping -- no service involved.
# ---------------------------------------------------------------------------


@pytest.fixture
def reader_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        yield db, engine
    finally:
        db.close()


def _seed_department(db, *, id, tenant_id, organization_id, code, name):
    from datetime import datetime, timezone

    db.add(
        DepartmentORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            department_code=code,
            name=name,
            is_active=True,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            version=1,
        )
    )


def _seed_site(db, *, id, tenant_id, organization_id, code, name):
    from datetime import datetime, timezone

    db.add(
        SiteORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            site_code=code,
            name=name,
            is_active=True,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            version=1,
        )
    )


def _seed_employee(db, *, id, tenant_id, organization_id, code, is_active, department_id=None, site_id=None):
    db.add(
        EmployeeORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            employee_code=code,
            full_name=f"Employee {code}",
            is_active=is_active,
            department_id=department_id,
            site_id=site_id,
            version=1,
        )
    )


def _count_selects(engine, table_name, fn):
    statements = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        if table_name in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
    return result, len(statements)


def test_department_breakdown_empty_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyEmployeeHeadcountReader(db)

    rows = reader.get_department_breakdown(tenant_id="tenant-a", organization_id="org-a")

    assert rows == ()


def test_department_breakdown_groups_and_labels_unassigned(reader_session):
    db, engine = reader_session
    _seed_department(db, id="d1", tenant_id="tenant-a", organization_id="org-a", code="D1", name="Engineering")
    _seed_department(db, id="d2", tenant_id="tenant-a", organization_id="org-a", code="D2", name="Sales")
    _seed_employee(db, id="e1", tenant_id="tenant-a", organization_id="org-a", code="E1", is_active=True, department_id="d1")
    _seed_employee(db, id="e2", tenant_id="tenant-a", organization_id="org-a", code="E2", is_active=False, department_id="d1")
    _seed_employee(db, id="e3", tenant_id="tenant-a", organization_id="org-a", code="E3", is_active=True, department_id="d2")
    _seed_employee(db, id="e4", tenant_id="tenant-a", organization_id="org-a", code="E4", is_active=True, department_id=None)
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)
    rows = reader.get_department_breakdown(tenant_id="tenant-a", organization_id="org-a")

    by_name = {row.department_name: row for row in rows}
    assert set(by_name) == {"Engineering", "Sales", "Unassigned"}
    assert (by_name["Engineering"].total, by_name["Engineering"].active) == (2, 1)
    assert (by_name["Sales"].total, by_name["Sales"].active) == (1, 1)
    assert (by_name["Unassigned"].total, by_name["Unassigned"].active) == (1, 1)
    assert by_name["Unassigned"].department_id is None
    assert by_name["Engineering"].department_id == "d1"


def test_department_breakdown_orders_alphabetically_with_unassigned_last(reader_session):
    db, engine = reader_session
    _seed_department(db, id="d1", tenant_id="tenant-a", organization_id="org-a", code="D1", name="Zulu")
    _seed_department(db, id="d2", tenant_id="tenant-a", organization_id="org-a", code="D2", name="Alpha")
    _seed_employee(db, id="e1", tenant_id="tenant-a", organization_id="org-a", code="E1", is_active=True, department_id="d1")
    _seed_employee(db, id="e2", tenant_id="tenant-a", organization_id="org-a", code="E2", is_active=True, department_id="d2")
    _seed_employee(db, id="e3", tenant_id="tenant-a", organization_id="org-a", code="E3", is_active=True, department_id=None)
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)
    rows = reader.get_department_breakdown(tenant_id="tenant-a", organization_id="org-a")

    assert [row.department_name for row in rows] == ["Alpha", "Zulu", "Unassigned"]


def test_department_breakdown_isolated_by_organization_and_tenant(reader_session):
    db, engine = reader_session
    _seed_department(db, id="d1", tenant_id="tenant-a", organization_id="org-a", code="D1", name="Dept A")
    _seed_department(db, id="d2", tenant_id="tenant-a", organization_id="org-b", code="D2", name="Dept B")
    _seed_employee(db, id="e1", tenant_id="tenant-a", organization_id="org-a", code="E1", is_active=True, department_id="d1")
    _seed_employee(db, id="e2", tenant_id="tenant-a", organization_id="org-b", code="E2", is_active=True, department_id="d2")
    _seed_employee(db, id="e3", tenant_id="tenant-b", organization_id="org-a", code="E3", is_active=True, department_id="d1")
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)

    rows_a = reader.get_department_breakdown(tenant_id="tenant-a", organization_id="org-a")
    assert [(row.department_name, row.total) for row in rows_a] == [("Dept A", 1)]

    rows_b = reader.get_department_breakdown(tenant_id="tenant-a", organization_id="org-b")
    assert [(row.department_name, row.total) for row in rows_b] == [("Dept B", 1)]

    rows_wrong_tenant = reader.get_department_breakdown(tenant_id="tenant-b", organization_id="org-a")
    assert [(row.department_name, row.total) for row in rows_wrong_tenant] == [("Dept A", 1)]


def test_department_breakdown_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    _seed_department(db, id="d1", tenant_id="tenant-a", organization_id="org-a", code="D1", name="Dept A")
    for i in range(10):
        _seed_employee(db, id=f"e{i}", tenant_id="tenant-a", organization_id="org-a", code=f"E{i}", is_active=True, department_id="d1")
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)
    _, statement_count = _count_selects(
        engine, "employees", lambda: reader.get_department_breakdown(tenant_id="tenant-a", organization_id="org-a")
    )

    assert statement_count == 1


def test_site_breakdown_empty_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyEmployeeHeadcountReader(db)

    rows = reader.get_site_breakdown(tenant_id="tenant-a", organization_id="org-a")

    assert rows == ()


def test_site_breakdown_groups_and_labels_unassigned(reader_session):
    db, engine = reader_session
    _seed_site(db, id="s1", tenant_id="tenant-a", organization_id="org-a", code="S1", name="Berlin")
    _seed_employee(db, id="e1", tenant_id="tenant-a", organization_id="org-a", code="E1", is_active=True, site_id="s1")
    _seed_employee(db, id="e2", tenant_id="tenant-a", organization_id="org-a", code="E2", is_active=False, site_id=None)
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)
    rows = reader.get_site_breakdown(tenant_id="tenant-a", organization_id="org-a")

    by_name = {row.site_name: row for row in rows}
    assert (by_name["Berlin"].total, by_name["Berlin"].active) == (1, 1)
    assert (by_name["Unassigned"].total, by_name["Unassigned"].active) == (1, 0)
    assert by_name["Unassigned"].site_id is None


def test_site_breakdown_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    _seed_site(db, id="s1", tenant_id="tenant-a", organization_id="org-a", code="S1", name="Berlin")
    for i in range(10):
        _seed_employee(db, id=f"e{i}", tenant_id="tenant-a", organization_id="org-a", code=f"E{i}", is_active=True, site_id="s1")
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)
    _, statement_count = _count_selects(
        engine, "employees", lambda: reader.get_site_breakdown(tenant_id="tenant-a", organization_id="org-a")
    )

    assert statement_count == 1


# ---------------------------------------------------------------------------
# Service + desktop API level tests through the real `services` fixture.
# ---------------------------------------------------------------------------


def test_employee_service_get_department_breakdown_reflects_writes(services):
    employee_service = services["employee_service"]
    department_service = services["department_service"]

    dept = department_service.create_department(department_code="BRK-D1", name="Breakdown Dept", is_active=True)
    employee_service.create_employee(employee_code="BRK-E1", full_name="Breakdown One", department_id=dept.id, is_active=True)
    employee_service.create_employee(employee_code="BRK-E2", full_name="Breakdown Two", department_id=dept.id, is_active=False)

    rows = employee_service.get_department_breakdown()
    by_name = {row.department_name: row for row in rows}
    assert (by_name["Breakdown Dept"].total, by_name["Breakdown Dept"].active) == (2, 1)


def test_employee_service_get_site_breakdown_reflects_writes(services):
    employee_service = services["employee_service"]
    site_service = services["site_service"]

    site = site_service.create_site(site_code="BRK-S1", name="Breakdown Site", is_active=True)
    employee_service.create_employee(employee_code="BRK-E3", full_name="Breakdown Three", site_id=site.id, is_active=True)

    rows = employee_service.get_site_breakdown()
    by_name = {row.site_name: row for row in rows}
    assert (by_name["Breakdown Site"].total, by_name["Breakdown Site"].active) == (1, 1)


def test_desktop_api_get_department_and_site_breakdown(services):
    from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi

    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]
    api = PlatformEmployeeDesktopApi(employee_service=employee_service)

    dept = department_service.create_department(department_code="BRK-API-D", name="API Dept", is_active=True)
    site = site_service.create_site(site_code="BRK-API-S", name="API Site", is_active=True)
    employee_service.create_employee(employee_code="BRK-API-E1", full_name="API One", department_id=dept.id, site_id=site.id, is_active=True)

    department_result = api.get_department_breakdown()
    site_result = api.get_site_breakdown()

    assert department_result.ok
    assert any(row.department_name == "API Dept" and row.total == 1 for row in department_result.data)
    assert site_result.ok
    assert any(row.site_name == "API Site" and row.total == 1 for row in site_result.data)


# ---------------------------------------------------------------------------
# End-to-end: the real admin overview presenter must surface real breakdown
# cards instead of the old hardcoded "Not yet available" placeholder.
# ---------------------------------------------------------------------------


def test_admin_overview_shows_real_breakdown_cards_not_placeholder(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    employee_service = services["employee_service"]
    department_service = services["department_service"]

    dept = department_service.create_department(department_code="BRK-OV-D", name="Overview Dept", is_active=True)
    employee_service.create_employee(employee_code="BRK-OV-E1", full_name="Overview One", department_id=dept.id, is_active=True)

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    admin = catalog.adminOverview()

    cards_by_title = {card["title"]: card for card in admin["breakdownCards"]}
    assert "Employees by Department" in cards_by_title
    assert "Employees by Site" in cards_by_title
    department_rows = {row["label"]: row for row in cards_by_title["Employees by Department"]["rows"]}
    assert department_rows["Overview Dept"]["value"] == "1"
    # The old hardcoded backlog placeholder text must be gone entirely.
    assert "Not yet available" not in str(admin)
    assert "tracked as backlog" not in str(admin)


def test_admin_overview_has_no_audit_activity_feed(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    admin = catalog.adminOverview()

    assert "activityFeed" not in admin
