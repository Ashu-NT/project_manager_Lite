from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.financials.models.finance_change_facts import (
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_change_reader import (
    SqlAlchemyFinanceChangeReader,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6b-change-tenant-a"
TENANT_B = "r6b-change-tenant-b"
ORG_A = "r6b-change-org-a"
ORG_B = "r6b-change-org-b"
PROJECT_A = "r6b-change-project-a"
PROJECT_B = "r6b-change-project-b"


def _seed_scope(connection, *, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
    project_id = f"r6b-change-project-{suffix}"
    code_id = f"r6b-change-code-{suffix}"
    connection.execute(
        text(
            "INSERT INTO organizations "
            "(id, tenant_id, organization_code, display_name, timezone_name, "
            "base_currency, is_enabled, version) "
            "VALUES (:id, :tenant, :code, :name, 'UTC', 'USD', true, 1)"
        ),
        {
            "id": organization_id,
            "tenant": tenant_id,
            "code": f"R6B-CHANGE-ORG-{suffix.upper()}",
            "name": f"R6B Change Organization {suffix.upper()}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO projects "
            "(id, tenant_id, project_code, name, description, status, "
            "organization_id, version) "
            "VALUES (:id, :tenant, :code, :name, '', 'ACTIVE', :organization, 1)"
        ),
        {
            "id": project_id,
            "tenant": tenant_id,
            "code": f"R6B-CHANGE-P-{suffix.upper()}",
            "name": f"R6B Change Project {suffix.upper()}",
            "organization": organization_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_cost_codes "
            "(id, tenant_id, organization_id, code, name, description, is_active, "
            "version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :code, :name, '', true, 1, :now, :now)"
        ),
        {
            "id": code_id,
            "tenant": tenant_id,
            "organization": organization_id,
            "code": f"R6B-CHANGE-{suffix.upper()}",
            "name": f"R6B Change {suffix.upper()}",
            "now": now,
        },
    )
    request_count = 2 if suffix == "a" else 1
    for index in range(1, request_count + 1):
        change_id = f"r6b-change-request-{suffix}-{index}"
        approval_id = f"r6b-change-approval-{suffix}-{index}"
        connection.execute(
            text(
                "INSERT INTO approval_requests "
                "(id, tenant_id, request_type, entity_type, entity_id, organization_id, "
                "project_id, payload_json, status, requested_by_username, requested_at) "
                "VALUES (:id, :tenant, 'financial_change.apply', 'financial_change', "
                ":entity, :organization, :project, '{}', 'PENDING', :requester, :now)"
            ),
            {
                "id": approval_id,
                "tenant": tenant_id,
                "entity": change_id,
                "organization": organization_id,
                "project": project_id,
                "requester": f"requester-{suffix}",
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO project_finance_change_requests "
                "(id, tenant_id, organization_id, project_id, title, reason, description, "
                "effective_date, currency_code, created_by, revision, status, "
                "approval_request_id, submitted_by, submitted_at, version, created_at, updated_at) "
                "VALUES (:id, :tenant, :organization, :project, :title, :reason, '', "
                "'2026-09-01', 'USD', :requester, :revision, 'pending_approval', "
                ":approval, :requester, :now, 1, :now, :now)"
            ),
            {
                "id": change_id,
                "tenant": tenant_id,
                "organization": organization_id,
                "project": project_id,
                "title": f"Change {index} {suffix.upper()}",
                "reason": f"Governed reason {index}",
                "requester": f"requester-{suffix}",
                "revision": index,
                "approval": approval_id,
                "now": now,
            },
        )
    for index, impact_type in enumerate(("budget", "forecast"), start=1):
        if suffix != "a" and index > 1:
            break
        connection.execute(
            text(
                "INSERT INTO project_finance_change_impacts "
                "(id, tenant_id, organization_id, change_request_id, project_id, "
                "impact_type, description, amount, currency_code, cost_code_id, created_at) "
                "VALUES (:id, :tenant, :organization, :change, :project, :type, "
                ":description, :amount, 'USD', :code, :now)"
            ),
            {
                "id": f"r6b-change-impact-{suffix}-{index}",
                "tenant": tenant_id,
                "organization": organization_id,
                "change": f"r6b-change-request-{suffix}-1",
                "project": project_id,
                "type": impact_type,
                "description": f"{impact_type.title()} impact {suffix.upper()}",
                "amount": Decimal("125.2500") if index == 1 else Decimal("80.5000"),
                "code": code_id,
                "now": now,
            },
        )


@pytest.fixture(scope="module", autouse=True)
def seeded_change_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6B-CHANGE-A"), (TENANT_B, "R6B-CHANGE-B")):
            connection.execute(
                text(
                    "INSERT INTO tenants "
                    "(id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:id, :code, :code, 'active', true, 1)"
                ),
                {"id": tenant_id, "code": code},
            )
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


def test_change_reader_is_bounded_through_runtime_rls_role(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinanceChangeReader(session=session)
        changes, master_statements = _count_selects(
            session,
            lambda: reader.list_changes(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                request=FinancialChangeRequestQuery(
                    page_size=25, status="pending_approval", approval_status="pending"
                ),
            ),
        )
        selected, detail_statements = _count_selects(
            session,
            lambda: reader.get_change(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                change_id="r6b-change-request-a-1",
            ),
        )
        impacts, impact_statements = _count_selects(
            session,
            lambda: reader.list_impacts(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                change_id="r6b-change-request-a-1",
                request=FinancialChangeImpactQuery(page_size=25),
            ),
        )
        assert master_statements == 2
        assert detail_statements == 1
        assert impact_statements == 2
        assert changes.total == 2
        assert selected is not None and selected.impact_count == 2
        assert impacts.total == 2
        assert {item.impact_type for item in impacts.items} == {"budget", "forecast"}
        assert impacts.items[0].amount in {Decimal("125.2500"), Decimal("80.5000")}
    finally:
        session.close()


def test_change_reader_and_direct_impact_table_deny_cross_scope(
    postgres_test_environment,
):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        reader = SqlAlchemyFinanceChangeReader(session=session)
        foreign = reader.list_changes(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            request=FinancialChangeRequestQuery(),
        )
        assert foreign.total == 0
        assert reader.get_change(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            change_id="r6b-change-request-b-1",
        ) is None
        foreign_impacts = reader.list_impacts(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            change_id="r6b-change-request-b-1",
            request=FinancialChangeImpactQuery(),
        )
        assert foreign_impacts.total == 0
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_change_requests "
                "WHERE id = 'r6b-change-request-b-1'"
            )
        ) == 0
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_change_impacts "
                "WHERE id = 'r6b-change-impact-b-1'"
            )
        ) == 0
    finally:
        session.close()


def test_change_reader_postgresql_plans_are_bounded(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        statements = {
            "master": (
                "SELECT c.id, c.title, c.status FROM project_finance_change_requests c "
                "WHERE c.tenant_id = :tenant AND c.organization_id = :organization "
                "AND c.project_id = :project AND c.status = 'pending_approval' "
                "ORDER BY c.created_at DESC, c.id ASC LIMIT 25"
            ),
            "impacts": (
                "SELECT i.id, i.impact_type, i.amount FROM project_finance_change_impacts i "
                "WHERE i.tenant_id = :tenant AND i.organization_id = :organization "
                "AND i.project_id = :project AND i.change_request_id = :change "
                "ORDER BY i.created_at ASC, i.id ASC LIMIT 25"
            ),
        }
        params = {
            "tenant": TENANT_A,
            "organization": ORG_A,
            "project": PROJECT_A,
            "change": "r6b-change-request-a-1",
        }
        for name, statement in statements.items():
            plan = "\n".join(
                session.execute(
                    text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {statement}"), params
                ).scalars()
            )
            assert "Limit" in plan, (name, plan)
            assert "Execution Time" in plan, (name, plan)
    finally:
        session.close()
