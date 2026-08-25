from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.tenant.modules.modules import ModuleEntitlementORM
from src.core.platform.infrastructure.persistence.read.tenant.modules.module_entitlement_reader import (
    SqlAlchemyModuleEntitlementReader,
)
from src.infra.persistence.orm import Base


# ---------------------------------------------------------------------------
# Reader-level unit tests: exact query count + tenancy scoping, no service
# involved. Mirrors how a CQRS reader is expected to behave in isolation.
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


def _seed_row(db, *, tenant_id, organization_id, module_code, licensed, enabled, lifecycle_status="active"):
    db.add(
        ModuleEntitlementORM(
            organization_id=organization_id,
            module_code=module_code,
            tenant_id=tenant_id,
            licensed=licensed,
            enabled=enabled,
            lifecycle_status=lifecycle_status,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )


def test_reader_issues_exactly_one_sql_statement(reader_session):
    db, engine = reader_session
    _seed_row(db, tenant_id="tenant-a", organization_id="org-a", module_code="project_management", licensed=True, enabled=True)
    _seed_row(db, tenant_id="tenant-a", organization_id="org-a", module_code="qhse", licensed=False, enabled=False)
    db.commit()

    queries = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    reader = SqlAlchemyModuleEntitlementReader(db)
    snapshot = reader.get_snapshot(tenant_id="tenant-a", organization_id="org-a")

    assert len(queries) == 1, f"expected exactly one SQL statement, got {len(queries)}: {queries}"
    assert snapshot.organization_id == "org-a"
    assert {r.module_code for r in snapshot.records} == {"project_management", "qhse"}
    pm_record = snapshot.record_for("project_management")
    assert pm_record is not None
    assert pm_record.licensed is True
    assert pm_record.enabled is True
    qhse_record = snapshot.record_for("qhse")
    assert qhse_record is not None
    assert qhse_record.licensed is False
    assert qhse_record.enabled is False
    assert snapshot.record_for("inventory_procurement") is None


def test_reader_scopes_strictly_by_organization_and_tenant(reader_session):
    """Defense in depth: the reader must never leak another organization's
    or another tenant's rows, even though it takes both ids as plain
    arguments rather than resolving them from ambient session state."""
    db, _engine = reader_session
    _seed_row(db, tenant_id="tenant-a", organization_id="org-a", module_code="project_management", licensed=True, enabled=True)
    _seed_row(db, tenant_id="tenant-a", organization_id="org-b", module_code="project_management", licensed=False, enabled=False)
    _seed_row(db, tenant_id="tenant-b", organization_id="org-c", module_code="project_management", licensed=True, enabled=True)
    db.commit()

    reader = SqlAlchemyModuleEntitlementReader(db)

    snapshot_a = reader.get_snapshot(tenant_id="tenant-a", organization_id="org-a")
    assert [r.module_code for r in snapshot_a.records] == ["project_management"]
    assert snapshot_a.record_for("project_management").licensed is True

    snapshot_b = reader.get_snapshot(tenant_id="tenant-a", organization_id="org-b")
    assert snapshot_b.record_for("project_management").licensed is False

    # org-a's rows are tenant-a's; asking for org-a under tenant-b must not
    # return them even though the organization_id string matches.
    snapshot_wrong_tenant = reader.get_snapshot(tenant_id="tenant-b", organization_id="org-a")
    assert snapshot_wrong_tenant.records == ()

    snapshot_c = reader.get_snapshot(tenant_id="tenant-b", organization_id="org-c")
    assert [r.module_code for r in snapshot_c.records] == ["project_management"]


def test_reader_dedupes_legacy_alias_preferring_canonical_code(reader_session):
    """'payroll' is a legacy alias for 'hr_management' (module_codes.py). If
    both rows exist, the reader must resolve to exactly one record per
    canonical code -- same precedence the write repository uses."""
    db, _engine = reader_session
    _seed_row(db, tenant_id="tenant-a", organization_id="org-a", module_code="hr_management", licensed=True, enabled=True)
    _seed_row(db, tenant_id="tenant-a", organization_id="org-a", module_code="payroll", licensed=False, enabled=False)
    db.commit()

    reader = SqlAlchemyModuleEntitlementReader(db)
    snapshot = reader.get_snapshot(tenant_id="tenant-a", organization_id="org-a")

    assert [r.module_code for r in snapshot.records] == ["hr_management"]
    assert snapshot.record_for("hr_management").licensed is True
    # normalize_module_code("payroll") == "hr_management" -- lookup by the
    # legacy alias must still resolve to the canonical record.
    assert snapshot.record_for("payroll").licensed is True


def test_reader_empty_snapshot_when_no_rows(reader_session):
    db, _engine = reader_session
    reader = SqlAlchemyModuleEntitlementReader(db)
    snapshot = reader.get_snapshot(tenant_id="tenant-a", organization_id="org-a")
    assert snapshot.records == ()
    assert snapshot.record_for("project_management") is None


# ---------------------------------------------------------------------------
# Service-level result-equivalence + tenancy tests, through the real
# composition root (services fixture) -- confirms ModuleCatalogService's
# CQRS-rewired read path (module_catalog_query.py/module_catalog_context.py)
# produces the same answers a caller would reasonably expect, and that
# switching the active organization switches the visible entitlement state.
# ---------------------------------------------------------------------------


def test_module_catalog_read_path_reflects_writes_through_the_reader(services):
    module_catalog = services["module_catalog_service"]
    active_org = services["organization_service"].get_active_organization()

    baseline = module_catalog.get_entitlement("project_management")
    assert baseline is not None
    assert baseline.licensed is True  # default-enabled per DEFAULT_ENTERPRISE_MODULES
    assert baseline.enabled is True

    module_catalog.set_module_state(active_org.id, "project_management", enabled=False)

    updated = module_catalog.get_entitlement("project_management")
    assert updated.licensed is True
    assert updated.enabled is False
    assert module_catalog.is_enabled("project_management") is False
    assert module_catalog.is_licensed("project_management") is True

    entitlements_by_code = {e.code: e for e in module_catalog.list_entitlements()}
    assert entitlements_by_code["project_management"].enabled is False
    assert "project_management" not in {m.code for m in module_catalog.list_enabled_modules()}
    assert "project_management" in {m.code for m in module_catalog.list_licensed_modules()}

    summary = module_catalog.shell_summary()
    enabled_section = summary.split("Enabled: ")[1].split(". Licensed:")[0]
    licensed_section = summary.split("Licensed: ")[1].split(". Available:")[0]
    assert entitlements_by_code["project_management"].label not in enabled_section.split(", ")
    assert entitlements_by_code["project_management"].label in licensed_section.split(", ")

    module_catalog.set_module_state(active_org.id, "project_management", licensed=False, enabled=False)
    catalog_snapshot = module_catalog.snapshot()
    assert "project_management" not in {m.code for m in catalog_snapshot.licensed_modules}
    assert "project_management" not in {m.code for m in catalog_snapshot.enabled_modules}
    assert "project_management" in {m.code for m in catalog_snapshot.available_modules}


def test_module_catalog_read_path_is_isolated_per_organization(services):
    organization_service = services["organization_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = organization_service.get_active_organization()
    second_organization = organization_service.create_organization(
        organization_code="SOUTH",
        display_name="South Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )

    # Disable on the default organization only. project_management defaults
    # to licensed=True/enabled=True (DEFAULT_ENTERPRISE_MODULES.default_enabled).
    module_catalog.set_module_state(default_organization.id, "project_management", enabled=False)
    assert module_catalog.is_enabled("project_management") is False

    organization_service.set_active_organization(second_organization.id)
    # A fresh organization must not inherit the default organization's
    # disabled state -- the reader must be scoped by the (now different)
    # active organization_id, not leak the previous snapshot.
    assert module_catalog.is_enabled("project_management") is True
    entitlements_by_code = {e.code: e for e in module_catalog.list_entitlements()}
    assert entitlements_by_code["project_management"].enabled is True

    organization_service.set_active_organization(default_organization.id)
    assert module_catalog.is_enabled("project_management") is False
    entitlements_by_code = {e.code: e for e in module_catalog.list_entitlements()}
    assert entitlements_by_code["project_management"].enabled is False


# ---------------------------------------------------------------------------
# P1.5 -- SQL-count guardrail: pins the fix so a future change to
# ModuleCatalogService can't silently reintroduce the confirmed 15-20-query
# N+1 (audit §7 R7a / §17) this pilot closed. Counts only statements against
# organization_module_entitlements -- the unrelated single "organizations"
# lookup snapshot() does for its context_label is out of this pilot's scope
# and asserted separately below so it isn't silently absorbed by a loose bound.
# ---------------------------------------------------------------------------


def _count_entitlement_queries(session, fn):
    engine = session.get_bind()
    queries = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        if "organization_module_entitlements" in statement:
            queries.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
    return result, len(queries)


def test_list_entitlements_issues_exactly_one_entitlement_query(services, session):
    module_catalog = services["module_catalog_service"]
    module_catalog.list_entitlements()  # warm any lazy defaults-seeding path first

    _, query_count = _count_entitlement_queries(session, module_catalog.list_entitlements)
    assert query_count == 1, (
        f"list_entitlements() issued {query_count} organization_module_entitlements "
        "queries, expected exactly 1 -- the per-module N+1 this pilot fixed may have "
        "regressed."
    )


def test_shell_summary_issues_exactly_one_entitlement_query(services, session):
    module_catalog = services["module_catalog_service"]
    module_catalog.shell_summary()

    _, query_count = _count_entitlement_queries(session, module_catalog.shell_summary)
    assert query_count == 1, (
        f"shell_summary() issued {query_count} organization_module_entitlements queries, "
        "expected exactly 1."
    )


def test_snapshot_issues_exactly_one_entitlement_query(services, session):
    module_catalog = services["module_catalog_service"]
    module_catalog.snapshot()

    _, query_count = _count_entitlement_queries(session, module_catalog.snapshot)
    assert query_count == 1, (
        f"snapshot() issued {query_count} organization_module_entitlements queries, "
        "expected exactly 1 (its separate 'organizations' lookup for context_label is "
        "unrelated to this guardrail)."
    )


def test_is_enabled_and_get_entitlement_stay_at_one_query_each(services, session):
    module_catalog = services["module_catalog_service"]
    module_catalog.is_enabled("project_management")
    module_catalog.get_entitlement("project_management")

    _, is_enabled_count = _count_entitlement_queries(
        session, lambda: module_catalog.is_enabled("project_management")
    )
    _, get_entitlement_count = _count_entitlement_queries(
        session, lambda: module_catalog.get_entitlement("project_management")
    )
    assert is_enabled_count == 1
    assert get_entitlement_count == 1


def test_combined_shell_load_scales_with_call_count_not_module_count(services, session):
    """Three independent public reads (list_entitlements + shell_summary +
    snapshot) must cost exactly 3 entitlement queries -- one per logical
    read -- regardless of how many modules DEFAULT_ENTERPRISE_MODULES has,
    not 3*N as it did before this pilot (measured 17 total pre-fix for 5
    modules)."""
    module_catalog = services["module_catalog_service"]
    module_catalog.list_entitlements()

    def combined():
        module_catalog.list_entitlements()
        module_catalog.shell_summary()
        module_catalog.snapshot()

    _, query_count = _count_entitlement_queries(session, combined)
    assert query_count == 3, (
        f"combined shell load issued {query_count} organization_module_entitlements "
        "queries, expected exactly 3 (one per logical read call)."
    )
