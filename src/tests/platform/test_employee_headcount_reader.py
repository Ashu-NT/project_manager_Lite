"""P6 -- employee headcount rollup pilot.

Before this pilot, the Admin Console overview tiles
(PlatformAdminWorkspacePresenter.build_overview) computed employee counts
by calling list_employees(active_only=None) -- EmployeeService.list_employees,
which fully hydrates every Employee row for the active organization via
EmployeeRepository.list_for_organization -- then summed over the whole
in-memory list in Python (active_employee_count = sum(1 for e in employees
if e.is_active)), refreshed on nearly every admin mutation
(admin_refresh_service.py). This is Platform's first SQL-side rollup
(audit sec.14 #6 "no SQL-side rollups anywhere in Platform"): a single
aggregate query (COUNT + SUM(CASE...)) via EmployeeHeadcountReader replaces
the full-list materialization + Python sum, exactly the way P1's
ModuleEntitlementReader replaced module_catalog's per-module N+1.

These tests mirror test_module_entitlement_reader.py's structure: reader-
level unit tests (exact query count + tenancy scoping, isolated db), then
service-level and end-to-end (real admin presenter) equivalence/isolation
tests through the real `services` fixture, then SQL-count guardrails.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.infra.persistence.orm import Base


# ---------------------------------------------------------------------------
# Reader-level unit tests: exact query count + tenancy scoping, no service
# involved.
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


def _seed_employee(db, *, id, tenant_id, organization_id, code, is_active):
    db.add(
        EmployeeORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            employee_code=code,
            full_name=f"Employee {code}",
            is_active=is_active,
            version=1,
        )
    )


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
    return result, len(statements)


def test_reader_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    _seed_employee(db, id="e1", tenant_id="tenant-a", organization_id="org-a", code="E1", is_active=True)
    _seed_employee(db, id="e2", tenant_id="tenant-a", organization_id="org-a", code="E2", is_active=True)
    _seed_employee(db, id="e3", tenant_id="tenant-a", organization_id="org-a", code="E3", is_active=False)
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)
    summary, statement_count = _count_employee_selects(
        engine, lambda: reader.get_summary(tenant_id="tenant-a", organization_id="org-a")
    )

    assert statement_count == 1
    assert summary.total == 3
    assert summary.active == 2


def test_reader_scopes_strictly_by_organization_and_tenant(reader_session):
    db, engine = reader_session
    _seed_employee(db, id="e1", tenant_id="tenant-a", organization_id="org-a", code="E1", is_active=True)
    _seed_employee(db, id="e2", tenant_id="tenant-a", organization_id="org-a", code="E2", is_active=False)
    _seed_employee(db, id="e3", tenant_id="tenant-a", organization_id="org-b", code="E3", is_active=True)
    _seed_employee(db, id="e4", tenant_id="tenant-b", organization_id="org-a", code="E4", is_active=True)
    db.flush()

    reader = SqlAlchemyEmployeeHeadcountReader(db)

    summary_a = reader.get_summary(tenant_id="tenant-a", organization_id="org-a")
    assert (summary_a.total, summary_a.active) == (2, 1)

    summary_b = reader.get_summary(tenant_id="tenant-a", organization_id="org-b")
    assert (summary_b.total, summary_b.active) == (1, 1)

    # Same organization_id under the WRONG tenant must not be counted --
    # org-a exists under both tenant-a (2 employees) and tenant-b
    # (1 employee); each tenant's view must stay isolated.
    summary_wrong_tenant = reader.get_summary(tenant_id="tenant-b", organization_id="org-a")
    assert (summary_wrong_tenant.total, summary_wrong_tenant.active) == (1, 1)


def test_reader_empty_summary_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyEmployeeHeadcountReader(db)

    summary = reader.get_summary(tenant_id="tenant-a", organization_id="org-a")

    assert (summary.total, summary.active) == (0, 0)


# ---------------------------------------------------------------------------
# Service + end-to-end equivalence/isolation tests, through the real
# `services` fixture.
# ---------------------------------------------------------------------------


def test_employee_service_headcount_summary_reflects_writes(services):
    employee_service = services["employee_service"]

    baseline = employee_service.get_headcount_summary()

    employee_service.create_employee(employee_code="P6-E1", full_name="Employee One", is_active=True)
    employee_service.create_employee(employee_code="P6-E2", full_name="Employee Two", is_active=False)

    updated = employee_service.get_headcount_summary()
    assert updated.total == baseline.total + 2
    assert updated.active == baseline.active + 1


def test_employee_headcount_is_isolated_per_organization(services):
    organization_service = services["organization_service"]
    employee_service = services["employee_service"]

    default_organization = organization_service.get_active_organization()
    employee_service.create_employee(employee_code="P6-DEF-1", full_name="Default Org Employee", is_active=True)
    default_summary = employee_service.get_headcount_summary()
    assert default_summary.total >= 1

    second_organization = organization_service.create_organization(
        organization_code="P6-SECOND",
        display_name="Second Org",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    fresh_org_summary = employee_service.get_headcount_summary()
    assert (fresh_org_summary.total, fresh_org_summary.active) == (0, 0)

    employee_service.create_employee(employee_code="P6-SEC-1", full_name="Second Org Employee", is_active=True)
    assert employee_service.get_headcount_summary().total == 1

    organization_service.set_active_organization(default_organization.id)
    assert employee_service.get_headcount_summary().total == default_summary.total


# ---------------------------------------------------------------------------
# P6.5 -- SQL-count guardrail: pins the fix so a future change can't
# silently reintroduce the full-list-materialization pattern this pilot
# closed.
# ---------------------------------------------------------------------------


def _instrument_list_for_organization(employee_repo):
    counts = {"list_for_organization": 0}
    cls = type(employee_repo)
    real = cls.list_for_organization

    def counting(self, *args, **kwargs):
        counts["list_for_organization"] += 1
        return real(self, *args, **kwargs)

    cls.list_for_organization = counting

    def restore():
        cls.list_for_organization = real

    return counts, restore


def test_get_headcount_summary_never_calls_list_for_organization(services, session):
    employee_service = services["employee_service"]
    employee_repo = employee_service._employee_repo
    engine = session.get_bind()

    for i in range(50):
        employee_service.create_employee(
            employee_code=f"P6-BULK-{i}", full_name=f"Bulk Employee {i}", is_active=(i % 2 == 0)
        )

    counts, restore = _instrument_list_for_organization(employee_repo)
    try:
        _, selects = _count_employee_selects(
            engine, lambda: employee_service.get_headcount_summary()
        )
    finally:
        restore()

    assert counts["list_for_organization"] == 0, (
        "get_headcount_summary must never call the write repository's "
        "list_for_organization -- that would silently reintroduce the full-list "
        "materialization this pilot removed"
    )
    assert selects == 1


def test_admin_overview_never_lists_full_employee_collection(services):
    """End-to-end: the real Admin Console overview builder must use the
    headcount summary, not a full employee list, regardless of how many
    employees exist."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    employee_service = services["employee_service"]
    employee_repo = employee_service._employee_repo

    for i in range(20):
        employee_service.create_employee(
            employee_code=f"P6-ADMIN-{i}", full_name=f"Admin Overview Employee {i}", is_active=(i % 3 == 0)
        )
    expected = employee_service.get_headcount_summary()

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    counts, restore = _instrument_list_for_organization(employee_repo)
    try:
        admin = catalog.adminOverview()
    finally:
        restore()

    assert counts["list_for_organization"] == 0
    metrics_by_label = {m["label"]: m["value"] for m in admin["metrics"]}
    assert metrics_by_label["Employees"] == str(expected.active)
    rows_by_label = {
        row["label"]: row["supportingText"]
        for section in admin["sections"]
        for row in section["rows"]
        if section["title"] == "Identity And Workforce"
    }
    assert f"{expected.active} active employee records" == rows_by_label["Employees"]
