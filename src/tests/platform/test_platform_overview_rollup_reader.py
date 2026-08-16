"""Platform Overview rollup -- backend performance modernization.

Before this change, PlatformAdminWorkspacePresenter.build_overview() computed
Organizations/Sites/Departments/Parties/Documents counts by calling each
entity's list_X(active_only=None) -- fully hydrating every row for the active
organization -- then summing/len()-ing over the whole in-memory list in
Python. This mirrors the same anti-pattern P6 (test_employee_headcount_
reader.py) already fixed for Employees: a single aggregate SQL query
(COUNT + SUM(CASE...)) via a dedicated reader replaces the full-list
materialization + Python sum.

PlatformOverviewRollupReader is one cohesive overview-specific reader (not
one Reader per entity) covering Organizations, Sites, Departments, Parties,
and Documents. Employees keeps its own EmployeeHeadcountReader unchanged;
Users is deliberately out of scope for this phase (list_users() has
caller-type branching and a platform-role exclusion computed via per-user
role lookups that a naive COUNT would not safely replicate).

Sites additionally carries row-level scope restriction on top of the
permission check (SiteService.list_sites() applies filter_scope_rows()) --
SiteService.get_site_rollup_summary() replicates that restriction by passing
the caller's allowed_site_ids into the reader, verified below.

These tests mirror test_employee_headcount_reader.py's structure: reader-
level unit tests (exact query count + tenancy/organization scoping, isolated
db), then service-level tests through the real `services` fixture, then
end-to-end (real admin presenter) SQL-count guardrails.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import DocumentORM
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import PartyORM
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.infra.persistence.orm import Base


# ---------------------------------------------------------------------------
# Reader-level unit tests: exact query count + tenancy/organization scoping,
# no service involved.
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


_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _seed_organization(db, *, id, tenant_id, code):
    db.add(
        OrganizationORM(
            id=id,
            tenant_id=tenant_id,
            organization_code=code,
            display_name=f"Org {code}",
            version=1,
        )
    )


def _seed_site(db, *, id, tenant_id, organization_id, code, name, is_active):
    db.add(
        SiteORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            site_code=code,
            name=name,
            is_active=is_active,
            created_at=_NOW,
            updated_at=_NOW,
            version=1,
        )
    )


def _seed_department(db, *, id, tenant_id, organization_id, code, is_active):
    db.add(
        DepartmentORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            department_code=code,
            name=f"Department {code}",
            is_active=is_active,
            created_at=_NOW,
            updated_at=_NOW,
            version=1,
        )
    )


def _seed_party(db, *, id, tenant_id, organization_id, code, is_active):
    db.add(
        PartyORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            party_code=code,
            party_name=f"Party {code}",
            party_type="GENERAL",
            is_active=is_active,
            created_at=_NOW,
            updated_at=_NOW,
            version=1,
        )
    )


def _seed_document(db, *, id, tenant_id, organization_id, code, is_current):
    db.add(
        DocumentORM(
            id=id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            document_code=code,
            title=f"Document {code}",
            document_type="GENERAL",
            storage_kind="FILE_PATH",
            storage_uri=f"/docs/{code}.pdf",
            uploaded_at=_NOW,
            is_current=is_current,
            is_active=True,
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


# --- Organizations -----------------------------------------------------


def test_organization_count_zero_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    assert reader.get_organization_count(tenant_id="tenant-a") == 0


def test_organization_count_issues_exactly_one_sql_statement_and_scopes_by_tenant(reader_session):
    db, engine = reader_session
    _seed_organization(db, id="org-1", tenant_id="tenant-a", code="ORG1")
    _seed_organization(db, id="org-2", tenant_id="tenant-a", code="ORG2")
    _seed_organization(db, id="org-3", tenant_id="tenant-b", code="ORG3")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    total, statement_count = _count_selects(
        engine, "organizations", lambda: reader.get_organization_count(tenant_id="tenant-a")
    )

    assert statement_count == 1
    assert total == 2
    assert reader.get_organization_count(tenant_id="tenant-b") == 1
    assert reader.get_organization_count(tenant_id="tenant-c") == 0


# --- Sites ---------------------------------------------------------------


def test_site_summary_zero_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    summary = reader.get_site_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.active, summary.sample_names) == (0, 0, ())


def test_site_summary_counts_and_active_flag(reader_session):
    db, engine = reader_session
    _seed_site(db, id="s1", tenant_id="tenant-a", organization_id="org-a", code="S1", name="Berlin", is_active=True)
    _seed_site(db, id="s2", tenant_id="tenant-a", organization_id="org-a", code="S2", name="Dubai", is_active=True)
    _seed_site(db, id="s3", tenant_id="tenant-a", organization_id="org-a", code="S3", name="Cairo", is_active=False)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_site_summary(organization_id="org-a", tenant_id="tenant-a")

    assert summary.total == 3
    assert summary.active == 2


def test_site_summary_isolated_by_organization_and_tenant(reader_session):
    db, engine = reader_session
    _seed_site(db, id="s1", tenant_id="tenant-a", organization_id="org-a", code="S1", name="Berlin", is_active=True)
    _seed_site(db, id="s2", tenant_id="tenant-a", organization_id="org-b", code="S2", name="Dubai", is_active=True)
    _seed_site(db, id="s3", tenant_id="tenant-b", organization_id="org-a", code="S3", name="Cairo", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    assert reader.get_site_summary(organization_id="org-a", tenant_id="tenant-a").total == 1
    assert reader.get_site_summary(organization_id="org-b", tenant_id="tenant-a").total == 1
    # Same organization_id under the WRONG tenant must not be counted.
    assert reader.get_site_summary(organization_id="org-a", tenant_id="tenant-b").total == 1
    assert reader.get_site_summary(organization_id="org-a", tenant_id="tenant-c").total == 0


def test_site_summary_sample_names_top_3_alphabetical(reader_session):
    db, engine = reader_session
    for code, name in [("S1", "Zurich"), ("S2", "Amsterdam"), ("S3", "Berlin"), ("S4", "Cairo"), ("S5", "Dubai")]:
        _seed_site(db, id=f"site-{code}", tenant_id="tenant-a", organization_id="org-a", code=code, name=name, is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_site_summary(organization_id="org-a", tenant_id="tenant-a")

    assert summary.total == 5
    assert summary.sample_names == ("Amsterdam", "Berlin", "Cairo")


def test_site_summary_issues_exactly_two_sql_statements(reader_session):
    """One aggregate query for total/active, one limited query for sample
    names -- never a full row materialization of every site."""
    db, engine = reader_session
    for i in range(10):
        _seed_site(db, id=f"site-{i}", tenant_id="tenant-a", organization_id="org-a", code=f"S{i}", name=f"Site {i}", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    _, statement_count = _count_selects(
        engine, "sites", lambda: reader.get_site_summary(organization_id="org-a", tenant_id="tenant-a")
    )

    assert statement_count == 2


def test_site_summary_scope_restriction_filters_to_allowed_ids(reader_session):
    db, engine = reader_session
    _seed_site(db, id="s1", tenant_id="tenant-a", organization_id="org-a", code="S1", name="Berlin", is_active=True)
    _seed_site(db, id="s2", tenant_id="tenant-a", organization_id="org-a", code="S2", name="Dubai", is_active=True)
    _seed_site(db, id="s3", tenant_id="tenant-a", organization_id="org-a", code="S3", name="Cairo", is_active=False)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_site_summary(
        organization_id="org-a", tenant_id="tenant-a", allowed_site_ids=frozenset({"s1", "s3"})
    )

    assert summary.total == 2
    assert summary.active == 1
    assert summary.sample_names == ("Berlin", "Cairo")


def test_site_summary_scope_restriction_empty_allowed_ids_short_circuits_without_query(reader_session):
    db, engine = reader_session
    _seed_site(db, id="s1", tenant_id="tenant-a", organization_id="org-a", code="S1", name="Berlin", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary, statement_count = _count_selects(
        engine,
        "sites",
        lambda: reader.get_site_summary(organization_id="org-a", tenant_id="tenant-a", allowed_site_ids=frozenset()),
    )

    assert (summary.total, summary.active, summary.sample_names) == (0, 0, ())
    assert statement_count == 0


# --- Departments -----------------------------------------------------------


def test_department_summary_zero_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    summary = reader.get_department_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.active) == (0, 0)


def test_department_summary_counts_and_active_flag(reader_session):
    db, engine = reader_session
    _seed_department(db, id="d1", tenant_id="tenant-a", organization_id="org-a", code="D1", is_active=True)
    _seed_department(db, id="d2", tenant_id="tenant-a", organization_id="org-a", code="D2", is_active=False)
    _seed_department(db, id="d3", tenant_id="tenant-a", organization_id="org-a", code="D3", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_department_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.active) == (3, 2)


def test_department_summary_isolated_by_organization_and_tenant(reader_session):
    db, engine = reader_session
    _seed_department(db, id="d1", tenant_id="tenant-a", organization_id="org-a", code="D1", is_active=True)
    _seed_department(db, id="d2", tenant_id="tenant-a", organization_id="org-b", code="D2", is_active=True)
    _seed_department(db, id="d3", tenant_id="tenant-b", organization_id="org-a", code="D3", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    assert reader.get_department_summary(organization_id="org-a", tenant_id="tenant-a").total == 1
    assert reader.get_department_summary(organization_id="org-b", tenant_id="tenant-a").total == 1
    assert reader.get_department_summary(organization_id="org-a", tenant_id="tenant-b").total == 1
    assert reader.get_department_summary(organization_id="org-a", tenant_id="tenant-c").total == 0


def test_department_summary_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    for i in range(10):
        _seed_department(db, id=f"d{i}", tenant_id="tenant-a", organization_id="org-a", code=f"D{i}", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    _, statement_count = _count_selects(
        engine, "departments", lambda: reader.get_department_summary(organization_id="org-a", tenant_id="tenant-a")
    )

    assert statement_count == 1


# --- Parties -----------------------------------------------------------


def test_party_summary_zero_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    summary = reader.get_party_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.active) == (0, 0)


def test_party_summary_counts_and_active_flag(reader_session):
    db, engine = reader_session
    _seed_party(db, id="p1", tenant_id="tenant-a", organization_id="org-a", code="P1", is_active=True)
    _seed_party(db, id="p2", tenant_id="tenant-a", organization_id="org-a", code="P2", is_active=False)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_party_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.active) == (2, 1)


def test_party_summary_isolated_by_organization_and_tenant(reader_session):
    db, engine = reader_session
    _seed_party(db, id="p1", tenant_id="tenant-a", organization_id="org-a", code="P1", is_active=True)
    _seed_party(db, id="p2", tenant_id="tenant-a", organization_id="org-b", code="P2", is_active=True)
    _seed_party(db, id="p3", tenant_id="tenant-b", organization_id="org-a", code="P3", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    assert reader.get_party_summary(organization_id="org-a", tenant_id="tenant-a").total == 1
    assert reader.get_party_summary(organization_id="org-b", tenant_id="tenant-a").total == 1
    assert reader.get_party_summary(organization_id="org-a", tenant_id="tenant-b").total == 1
    assert reader.get_party_summary(organization_id="org-a", tenant_id="tenant-c").total == 0


def test_party_summary_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    for i in range(10):
        _seed_party(db, id=f"p{i}", tenant_id="tenant-a", organization_id="org-a", code=f"P{i}", is_active=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    _, statement_count = _count_selects(
        engine, "parties", lambda: reader.get_party_summary(organization_id="org-a", tenant_id="tenant-a")
    )

    assert statement_count == 1


# --- Documents -----------------------------------------------------------


def test_document_summary_zero_when_no_rows(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    summary = reader.get_document_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.current) == (0, 0)


def test_document_summary_counts_and_current_flag(reader_session):
    db, engine = reader_session
    _seed_document(db, id="doc1", tenant_id="tenant-a", organization_id="org-a", code="DOC1", is_current=True)
    _seed_document(db, id="doc2", tenant_id="tenant-a", organization_id="org-a", code="DOC2", is_current=False)
    _seed_document(db, id="doc3", tenant_id="tenant-a", organization_id="org-a", code="DOC3", is_current=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_document_summary(organization_id="org-a", tenant_id="tenant-a")

    assert (summary.total, summary.current) == (3, 2)


def test_document_summary_isolated_by_organization_and_tenant(reader_session):
    db, engine = reader_session
    _seed_document(db, id="doc1", tenant_id="tenant-a", organization_id="org-a", code="DOC1", is_current=True)
    _seed_document(db, id="doc2", tenant_id="tenant-a", organization_id="org-b", code="DOC2", is_current=True)
    _seed_document(db, id="doc3", tenant_id="tenant-b", organization_id="org-a", code="DOC3", is_current=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    assert reader.get_document_summary(organization_id="org-a", tenant_id="tenant-a").total == 1
    assert reader.get_document_summary(organization_id="org-b", tenant_id="tenant-a").total == 1
    assert reader.get_document_summary(organization_id="org-a", tenant_id="tenant-b").total == 1
    assert reader.get_document_summary(organization_id="org-a", tenant_id="tenant-c").total == 0


def test_document_summary_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    for i in range(10):
        _seed_document(db, id=f"doc{i}", tenant_id="tenant-a", organization_id="org-a", code=f"DOC{i}", is_current=True)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    _, statement_count = _count_selects(
        engine, "documents", lambda: reader.get_document_summary(organization_id="org-a", tenant_id="tenant-a")
    )

    assert statement_count == 1


# ---------------------------------------------------------------------------
# Service-level tests through the real `services` fixture.
# ---------------------------------------------------------------------------


def test_organization_service_get_organization_count_reflects_writes(services):
    organization_service = services["organization_service"]

    baseline = organization_service.get_organization_count()
    organization_service.create_organization(
        organization_code="ROLLUP-ORG-1",
        display_name="Rollup Org 1",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )

    assert organization_service.get_organization_count() == baseline + 1


def test_site_service_get_site_rollup_summary_reflects_writes(services):
    site_service = services["site_service"]

    baseline = site_service.get_site_rollup_summary()
    site_service.create_site(site_code="ROLLUP-S1", name="Rollup Site 1", is_active=True)
    site_service.create_site(site_code="ROLLUP-S2", name="Rollup Site 2", is_active=False)

    updated = site_service.get_site_rollup_summary()
    assert updated.total == baseline.total + 2
    assert updated.active == baseline.active + 1


def test_department_service_get_department_rollup_summary_reflects_writes(services):
    department_service = services["department_service"]

    baseline = department_service.get_department_rollup_summary()
    department_service.create_department(department_code="ROLLUP-D1", name="Rollup Dept 1", is_active=True)
    department_service.create_department(department_code="ROLLUP-D2", name="Rollup Dept 2", is_active=False)

    updated = department_service.get_department_rollup_summary()
    assert updated.total == baseline.total + 2
    assert updated.active == baseline.active + 1


def test_party_service_get_party_rollup_summary_reflects_writes(services):
    party_service = services["party_service"]

    baseline = party_service.get_party_rollup_summary()
    party_service.create_party(party_code="ROLLUP-P1", party_name="Rollup Party 1", is_active=True)
    party_service.create_party(party_code="ROLLUP-P2", party_name="Rollup Party 2", is_active=False)

    updated = party_service.get_party_rollup_summary()
    assert updated.total == baseline.total + 2
    assert updated.active == baseline.active + 1


def test_document_service_get_document_rollup_summary_reflects_writes(services):
    document_service = services["document_service"]

    baseline = document_service.get_document_rollup_summary()
    document_service.create_document(document_code="ROLLUP-DOC1", title="Rollup Doc 1", storage_uri="/docs/rollup-doc1.pdf", is_current=True)
    document_service.create_document(document_code="ROLLUP-DOC2", title="Rollup Doc 2", storage_uri="/docs/rollup-doc2.pdf", is_current=False)

    updated = document_service.get_document_rollup_summary()
    assert updated.total == baseline.total + 2
    assert updated.current == baseline.current + 1


def test_rollup_summaries_isolated_per_organization(services):
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    party_service = services["party_service"]
    document_service = services["document_service"]

    default_organization = organization_service.get_active_organization()
    site_service.create_site(site_code="ISO-S1", name="Iso Site 1", is_active=True)
    department_service.create_department(department_code="ISO-D1", name="Iso Dept 1", is_active=True)
    party_service.create_party(party_code="ISO-P1", party_name="Iso Party 1", is_active=True)
    document_service.create_document(document_code="ISO-DOC1", title="Iso Doc 1", storage_uri="/docs/iso-doc1.pdf", is_current=True)

    second_organization = organization_service.create_organization(
        organization_code="ISO-SECOND",
        display_name="Second Org",
        timezone_name="UTC",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    assert site_service.get_site_rollup_summary().total == 0
    assert department_service.get_department_rollup_summary().total == 0
    assert party_service.get_party_rollup_summary().total == 0
    assert document_service.get_document_rollup_summary().total == 0

    organization_service.set_active_organization(default_organization.id)
    assert site_service.get_site_rollup_summary().total >= 1
    assert department_service.get_department_rollup_summary().total >= 1
    assert party_service.get_party_rollup_summary().total >= 1
    assert document_service.get_document_rollup_summary().total >= 1


def test_site_rollup_summary_respects_scope_restriction(services):
    """SiteService.list_sites() restricts rows to the caller's site-scope
    grants via filter_scope_rows() when the caller is scope-restricted for
    the "site" scope type -- get_site_rollup_summary() must reflect the
    same restricted view, not the full organization's sites."""
    from src.core.platform.application.security.authorization import get_authorization_engine

    site_service = services["site_service"]
    site_a = site_service.create_site(site_code="SCOPE-A", name="Scope Site A", is_active=True)
    site_service.create_site(site_code="SCOPE-B", name="Scope Site B", is_active=True)

    engine = get_authorization_engine()
    unrestricted_summary = site_service.get_site_rollup_summary()
    assert unrestricted_summary.total >= 2

    original_is_scope_restricted = type(engine).is_scope_restricted
    original_scope_ids_for = type(engine).scope_ids_for

    def _fake_is_scope_restricted(self, user_session, scope_type):
        if scope_type == "site":
            return True
        return original_is_scope_restricted(self, user_session, scope_type)

    def _fake_scope_ids_for(self, user_session, scope_type, permission_code):
        if scope_type == "site":
            return frozenset({site_a.id})
        return original_scope_ids_for(self, user_session, scope_type, permission_code)

    type(engine).is_scope_restricted = _fake_is_scope_restricted
    type(engine).scope_ids_for = _fake_scope_ids_for
    try:
        restricted_summary = site_service.get_site_rollup_summary()
    finally:
        type(engine).is_scope_restricted = original_is_scope_restricted
        type(engine).scope_ids_for = original_scope_ids_for

    assert restricted_summary.total == 1
    assert restricted_summary.sample_names == (site_a.name,)


# ---------------------------------------------------------------------------
# SQL-count guardrails: pin the fix so a future change can't silently
# reintroduce the full-list-materialization pattern this phase closed.
# ---------------------------------------------------------------------------


def _instrument(cls, method_name):
    counts = {method_name: 0}
    real = getattr(cls, method_name)

    def counting(self, *args, **kwargs):
        counts[method_name] += 1
        return real(self, *args, **kwargs)

    setattr(cls, method_name, counting)

    def restore():
        setattr(cls, method_name, real)

    return counts, restore


def test_rollup_summaries_never_call_write_repository_list_methods(services):
    organization_service = services["organization_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    party_service = services["party_service"]
    document_service = services["document_service"]

    for i in range(20):
        site_service.create_site(site_code=f"SQL-S{i}", name=f"SQL Site {i}", is_active=(i % 2 == 0))
        department_service.create_department(department_code=f"SQL-D{i}", name=f"SQL Dept {i}", is_active=(i % 2 == 0))
        party_service.create_party(party_code=f"SQL-P{i}", party_name=f"SQL Party {i}", is_active=(i % 2 == 0))
        document_service.create_document(document_code=f"SQL-DOC{i}", title=f"SQL Doc {i}", storage_uri=f"/docs/sql-doc{i}.pdf", is_current=(i % 2 == 0))

    instrumented = [
        (type(organization_service._organization_repo), "list_all"),
        (type(site_service._site_repo), "list_for_organization"),
        (type(department_service._department_repo), "list_for_organization"),
        (type(party_service._party_repo), "list_for_organization"),
        (type(document_service._document_repo), "list_for_organization"),
    ]
    counters = []
    restores = []
    for cls, method_name in instrumented:
        counts, restore = _instrument(cls, method_name)
        counters.append(counts)
        restores.append(restore)

    try:
        organization_service.get_organization_count()
        site_service.get_site_rollup_summary()
        department_service.get_department_rollup_summary()
        party_service.get_party_rollup_summary()
        document_service.get_document_rollup_summary()
    finally:
        for restore in restores:
            restore()

    for counts in counters:
        for method_name, count in counts.items():
            assert count == 0, (
                f"rollup summary calls must never call the write repository's "
                f"{method_name} -- that would reintroduce full-list materialization"
            )


def test_admin_overview_never_lists_full_master_data_collections(services):
    """End-to-end: the real Admin Console overview builder must use the
    rollup summaries, not full list_X() collections, regardless of how many
    rows exist. Also captures the SQL/query-count shape of build_overview()
    before vs. after this phase's change (see docstring at top of file)."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog

    organization_service = services["organization_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    party_service = services["party_service"]
    document_service = services["document_service"]

    for i in range(15):
        site_service.create_site(site_code=f"OV-S{i}", name=f"Overview Site {i}", is_active=(i % 3 == 0))
        department_service.create_department(department_code=f"OV-D{i}", name=f"Overview Dept {i}", is_active=(i % 3 == 0))
        party_service.create_party(party_code=f"OV-P{i}", party_name=f"Overview Party {i}", is_active=(i % 3 == 0))
        document_service.create_document(document_code=f"OV-DOC{i}", title=f"Overview Doc {i}", storage_uri=f"/docs/ov-doc{i}.pdf", is_current=(i % 3 == 0))

    expected_organization_count = organization_service.get_organization_count()
    expected_site_summary = site_service.get_site_rollup_summary()
    expected_department_summary = department_service.get_department_rollup_summary()
    expected_party_summary = party_service.get_party_rollup_summary()
    expected_document_summary = document_service.get_document_rollup_summary()

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    instrumented = [
        (type(organization_service._organization_repo), "list_all"),
        (type(site_service._site_repo), "list_for_organization"),
        (type(department_service._department_repo), "list_for_organization"),
        (type(party_service._party_repo), "list_for_organization"),
        (type(document_service._document_repo), "list_for_organization"),
    ]
    counters = []
    restores = []
    for cls, method_name in instrumented:
        counts, restore = _instrument(cls, method_name)
        counters.append(counts)
        restores.append(restore)

    session = services["session"]
    engine = session.get_bind()
    statements = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        admin = catalog.adminOverview()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
        for restore in restores:
            restore()

    for counts in counters:
        for method_name, count in counts.items():
            assert count == 0, (
                f"Admin overview must never call the write repository's {method_name} "
                "to compute rollup metrics -- that would reintroduce full-list materialization"
            )

    # SQL query-count captured for build_overview(): this phase replaces N
    # full-table-scan + Python-sum passes (one per entity) with one narrow
    # aggregate query per entity (plus a second, LIMIT-3 query for Sites'
    # sample names) -- a fixed, row-count-independent number of statements
    # rather than one that grows with result-set size.
    master_data_tables = ("organizations", "sites", "departments", "parties", "documents")
    master_data_statements = [
        statement for statement in statements
        if any(table in statement for table in master_data_tables)
    ]
    assert len(master_data_statements) <= 6, (
        "build_overview() should issue at most one aggregate query per rollup entity "
        "(plus one extra for Sites' sample-name query), not one per displayed row"
    )

    metrics_by_label = {m["label"]: m["value"] for m in admin["metrics"]}
    assert metrics_by_label["Organizations"] == str(expected_organization_count)
    assert metrics_by_label["Sites"] == str(expected_site_summary.active)
    assert metrics_by_label["Departments"] == str(expected_department_summary.active)
    assert metrics_by_label["Documents"] == str(expected_document_summary.current)

    rows_by_section = {
        section["title"]: {row["label"]: row for row in section["rows"]}
        for section in admin["sections"]
    }
    assert rows_by_section["Identity And Workforce"]["Departments"]["value"] == str(expected_department_summary.total)
    master_data_rows = rows_by_section["Master Data Coverage"]
    assert master_data_rows["Sites"]["value"] == str(expected_site_summary.total)
    assert master_data_rows["Sites"]["supportingText"] == ", ".join(expected_site_summary.sample_names)
    assert master_data_rows["Parties"]["value"] == str(expected_party_summary.total)
    assert master_data_rows["Documents"]["value"] == str(expected_document_summary.total)
