from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusQuery,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingScheduleQuery,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_billing_reader import (
    SqlAlchemyFinanceBillingReader,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6b-billing-tenant-a"
TENANT_B = "r6b-billing-tenant-b"
ORG_A = "r6b-billing-org-a"
ORG_B = "r6b-billing-org-b"
PROJECT_A = "r6b-billing-project-a"
PROJECT_B = "r6b-billing-project-b"


def _seed_scope(connection, *, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
    project_id = f"r6b-billing-project-{suffix}"
    profile_id = f"r6b-billing-profile-{suffix}"
    schedule_id = f"r6b-billing-schedule-{suffix}"
    preparation_id = f"r6b-billing-preparation-{suffix}"
    line_id = f"r6b-billing-line-{suffix}"
    connection.execute(text(
        "INSERT INTO organizations (id, tenant_id, organization_code, display_name, timezone_name, base_currency, is_enabled, version) "
        "VALUES (:id, :tenant, :code, :name, 'UTC', 'USD', true, 1)"
    ), {"id": organization_id, "tenant": tenant_id, "code": f"R6B-BILL-{suffix.upper()}", "name": f"R6B Billing {suffix.upper()}"})
    connection.execute(text(
        "INSERT INTO projects (id, tenant_id, project_code, name, description, status, organization_id, version) "
        "VALUES (:id, :tenant, :code, :name, '', 'ACTIVE', :organization, 1)"
    ), {"id": project_id, "tenant": tenant_id, "code": f"R6B-BILL-P-{suffix.upper()}", "name": f"R6B Billing Project {suffix.upper()}", "organization": organization_id})
    connection.execute(text(
        "INSERT INTO project_billing_profiles "
        "(id, tenant_id, organization_id, project_id, currency_code, contract_reference, contract_value, customer_party_id, external_customer_reference, purchase_order_reference, cost_plus_markup_percent, payment_terms_days, retention_years, legal_hold, status, version, created_by, created_at, updated_by, updated_at) "
        "VALUES (:id, :tenant, :organization, :project, 'USD', :reference, 125000.25, NULL, NULL, NULL, 10, 30, 7, false, 'active', 1, 'admin', :now, 'admin', :now)"
    ), {"id": profile_id, "tenant": tenant_id, "organization": organization_id, "project": project_id, "reference": f"CONTRACT-{suffix.upper()}", "now": now})
    connection.execute(text(
        "INSERT INTO project_billing_schedule_lines "
        "(id, tenant_id, organization_id, project_id, billing_profile_id, name, amount, currency_code, due_date, acceptance_reference, status, version, created_by, created_at, updated_by, updated_at) "
        "VALUES (:id, :tenant, :organization, :project, :profile, :name, 5000.25, 'USD', '2026-09-01', :acceptance, 'ready', 1, 'admin', :now, 'admin', :now)"
    ), {"id": schedule_id, "tenant": tenant_id, "organization": organization_id, "project": project_id, "profile": profile_id, "name": f"Milestone {suffix.upper()}", "acceptance": f"ACCEPT-{suffix.upper()}", "now": now})
    connection.execute(text(
        "INSERT INTO project_billing_preparations "
        "(id, tenant_id, organization_id, project_id, billing_profile_id, preparation_number, billing_method, period_start, period_end, currency_code, idempotency_key, status, line_count, total_amount, rejection_notes, version, created_by, created_at, updated_at) "
        "VALUES (:id, :tenant, :organization, :project, :profile, :number, 'fixed_price', '2026-08-01', '2026-08-31', 'USD', :key, 'approved', 1, 5000.25, '', 1, 'admin', :now, :now)"
    ), {"id": preparation_id, "tenant": tenant_id, "organization": organization_id, "project": project_id, "profile": profile_id, "number": f"BP-{suffix.upper()}-1", "key": f"billing-key-{suffix}", "now": now})
    connection.execute(text(
        "INSERT INTO project_billing_preparation_lines "
        "(id, tenant_id, organization_id, project_id, preparation_id, source_type, source_id, source_revision, source_content_hash, description, source_date, quantity, unit, unit_rate, net_amount, currency_code, source_amount, created_at) "
        "VALUES (:id, :tenant, :organization, :project, :preparation, 'schedule_line', :source, '1', :hash, :description, '2026-09-01', 1, 'milestone', 5000.25, 5000.25, 'USD', 5000.25, :now)"
    ), {"id": line_id, "tenant": tenant_id, "organization": organization_id, "project": project_id, "preparation": preparation_id, "source": schedule_id, "hash": suffix * 64, "description": f"Accepted milestone {suffix.upper()}", "now": now})
    connection.execute(text(
        "INSERT INTO project_billing_source_locks "
        "(id, tenant_id, organization_id, project_id, source_type, source_id, source_revision, source_content_hash, preparation_id, preparation_line_id, status, reserved_at, finalized_at) "
        "VALUES (:id, :tenant, :organization, :project, 'schedule_line', :source, '1', :hash, :preparation, :line, 'finalized', :now, :now)"
    ), {"id": f"r6b-billing-lock-{suffix}", "tenant": tenant_id, "organization": organization_id, "project": project_id, "source": schedule_id, "hash": suffix * 64, "preparation": preparation_id, "line": line_id, "now": now})
    connection.execute(text(
        "INSERT INTO project_billing_external_events "
        "(id, tenant_id, organization_id, project_id, preparation_id, event_type, external_system, external_status, idempotency_key, occurred_at, external_invoice_reference, message, recorded_at) "
        "VALUES (:id, :tenant, :organization, :project, :preparation, 'delivery_accepted', 'ACCOUNTING', 'accepted', :key, :now, :invoice, '', :now)"
    ), {"id": f"r6b-billing-event-{suffix}", "tenant": tenant_id, "organization": organization_id, "project": project_id, "preparation": preparation_id, "key": f"billing-event-key-{suffix}", "invoice": f"INV-{suffix.upper()}", "now": now})


@pytest.fixture(scope="module", autouse=True)
def seeded_billing_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6B-BILL-A"), (TENANT_B, "R6B-BILL-B")):
            connection.execute(text(
                "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                "VALUES (:id, :code, :code, 'active', true, 1)"
            ), {"id": tenant_id, "code": code})
        _seed_scope(connection, suffix="a", tenant_id=TENANT_A, organization_id=ORG_A)
        _seed_scope(connection, suffix="b", tenant_id=TENANT_B, organization_id=ORG_B)
        connection.execute(text("ANALYZE"))


def _count_selects(session, operation) -> tuple[object, int]:
    session.execute(text("SELECT 1"))
    statements = 0

    def before(_conn, _cursor, statement, _params, _context, _many):
        nonlocal statements
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements += 1

    event.listen(session.get_bind(), "before_cursor_execute", before)
    try:
        return operation(), statements
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", before)


def test_billing_reader_is_bounded_through_runtime_rls_role(postgres_test_environment):
    session = postgres_test_environment.runtime_session(tenant_id=TENANT_A, organization_id=ORG_A)
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinanceBillingReader(session=session)
        profile, profile_count = _count_selects(session, lambda: reader.get_profile(tenant_id=TENANT_A, organization_id=ORG_A, project_id=PROJECT_A))
        schedule, schedule_count = _count_selects(session, lambda: reader.list_schedule(tenant_id=TENANT_A, organization_id=ORG_A, project_id=PROJECT_A, request=BillingScheduleQuery(page_size=25)))
        preparations, preparation_count = _count_selects(session, lambda: reader.list_preparations(tenant_id=TENANT_A, organization_id=ORG_A, project_id=PROJECT_A, request=BillingPreparationQuery(page_size=25)))
        detail, detail_count = _count_selects(session, lambda: reader.get_preparation(tenant_id=TENANT_A, organization_id=ORG_A, project_id=PROJECT_A, preparation_id="r6b-billing-preparation-a"))
        lines, line_count = _count_selects(session, lambda: reader.list_preparation_lines(tenant_id=TENANT_A, organization_id=ORG_A, project_id=PROJECT_A, preparation_id="r6b-billing-preparation-a", request=BillingPreparationLineQuery(page_size=25)))
        assert (profile_count, schedule_count, preparation_count, detail_count, line_count) == (1, 2, 2, 1, 2)
        assert profile is not None and profile.contract_value == Decimal("125000.2500")
        assert schedule.total == 1 and schedule.items[0].source_state == "finalized"
        assert preparations.total == 1 and preparations.items[0].latest_external_status == "accepted"
        assert detail is not None and detail.finalized_lock_count == 1
        assert lines.total == 1 and lines.items[0].net_amount == Decimal("5000.2500")
    finally:
        session.close()


def test_accounting_status_reader_is_isolated_and_rls_scoped(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinanceBillingReader(session=session)
        page, query_count = _count_selects(
            session,
            lambda: reader.list_accounting_statuses(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                request=AccountingStatusQuery(page_size=1, search="ACCOUNTING"),
            ),
        )
        assert query_count == 2
        assert page.total == 1
        assert page.items[0].latest_external_status == "accepted"
        assert page.items[0].latest_external_invoice_reference == "INV-A"
        assert reader.list_accounting_statuses(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            request=AccountingStatusQuery(),
        ).total == 0
    finally:
        session.close()


def test_billing_tables_deny_cross_tenant_and_organization_direct_access(postgres_test_environment):
    session = postgres_test_environment.runtime_session(tenant_id=TENANT_A, organization_id=ORG_A)
    try:
        reader = SqlAlchemyFinanceBillingReader(session=session)
        assert reader.get_profile(tenant_id=TENANT_B, organization_id=ORG_B, project_id=PROJECT_B) is None
        assert reader.list_schedule(tenant_id=TENANT_B, organization_id=ORG_B, project_id=PROJECT_B, request=BillingScheduleQuery()).total == 0
        assert reader.list_preparations(tenant_id=TENANT_B, organization_id=ORG_B, project_id=PROJECT_B, request=BillingPreparationQuery()).total == 0
        tables = (
            "project_billing_profiles", "project_billing_schedule_lines",
            "project_billing_preparations", "project_billing_preparation_lines",
            "project_billing_source_locks", "project_billing_external_events",
        )
        for table in tables:
            assert session.scalar(text(f"SELECT count(*) FROM {table} WHERE tenant_id = :tenant AND organization_id = :organization"), {"tenant": TENANT_B, "organization": ORG_B}) == 0
    finally:
        session.close()


def test_billing_postgresql_material_plans_are_bounded(postgres_test_environment):
    session = postgres_test_environment.runtime_session(tenant_id=TENANT_A, organization_id=ORG_A)
    try:
        statements = (
            "SELECT id FROM project_billing_schedule_lines WHERE tenant_id=:tenant AND organization_id=:organization AND project_id=:project ORDER BY due_date, id LIMIT 25",
            "SELECT id FROM project_billing_preparations WHERE tenant_id=:tenant AND organization_id=:organization AND project_id=:project ORDER BY created_at DESC, id LIMIT 25",
            "SELECT id FROM project_billing_preparation_lines WHERE tenant_id=:tenant AND organization_id=:organization AND project_id=:project AND preparation_id=:preparation ORDER BY source_date, id LIMIT 25",
        )
        params = {"tenant": TENANT_A, "organization": ORG_A, "project": PROJECT_A, "preparation": "r6b-billing-preparation-a"}
        for statement in statements:
            plan = "\n".join(session.execute(text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {statement}"), params).scalars())
            assert "Limit" in plan
            assert "Execution Time" in plan
    finally:
        session.close()
