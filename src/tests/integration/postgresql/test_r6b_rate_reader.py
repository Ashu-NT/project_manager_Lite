from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    RateCardRequest,
    RateLineRequest,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_rate_reader import (
    SqlAlchemyFinanceRateReader,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6b-rate-tenant-a"
TENANT_B = "r6b-rate-tenant-b"
ORG_A = "r6b-rate-org-a"
ORG_B = "r6b-rate-org-b"
PROJECT_A = "r6b-rate-project-a"
PROJECT_B = "r6b-rate-project-b"


def _seed_scope(connection, *, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
    project_id = f"r6b-rate-project-{suffix}"
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
            "code": f"R6B-RATE-ORG-{suffix.upper()}",
            "name": f"R6B Rate Organization {suffix.upper()}",
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
            "code": f"R6B-RATE-P-{suffix.upper()}",
            "name": f"R6B Rate Project {suffix.upper()}",
            "organization": organization_id,
        },
    )
    for scope_name, card_project in (("organization", None), ("project", project_id)):
        card_id = f"r6b-rate-card-{scope_name}-{suffix}"
        connection.execute(
            text(
                "INSERT INTO project_finance_rate_cards "
                "(id, tenant_id, organization_id, project_id, name, version, "
                "is_active, created_at, updated_at) "
                "VALUES (:id, :tenant, :organization, :project, :name, 1, true, :now, :now)"
            ),
            {
                "id": card_id,
                "tenant": tenant_id,
                "organization": organization_id,
                "project": card_project,
                "name": f"{scope_name.title()} Rates {suffix.upper()}",
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO project_finance_rate_card_lines "
                "(id, tenant_id, organization_id, rate_card_id, rate_type, origin, "
                "role, effective_from, is_active, unit, rate_amount, rate_currency, "
                "version, created_at, updated_at) "
                "VALUES (:id, :tenant, :organization, :card, 'cost', 'configured', "
                ":role, '2026-01-01', true, 'HOUR', 125.2500, 'USD', 1, :now, :now)"
            ),
            {
                "id": f"r6b-rate-line-{scope_name}-{suffix}",
                "tenant": tenant_id,
                "organization": organization_id,
                "card": card_id,
                "role": f"engineer-{scope_name}-{suffix}",
                "now": now,
            },
        )


@pytest.fixture(scope="module", autouse=True)
def seeded_rate_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6B-RATE-A"), (TENANT_B, "R6B-RATE-B")):
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


def test_rate_reader_is_bounded_through_runtime_rls_role(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinanceRateReader(session=session)
        cards, card_statements = _count_selects(
            session,
            lambda: reader.list_cards(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                request=RateCardRequest(page_size=25, status="active"),
            ),
        )
        selected, selected_statements = _count_selects(
            session,
            lambda: reader.get_card(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                rate_card_id="r6b-rate-card-project-a",
            ),
        )
        lines, line_statements = _count_selects(
            session,
            lambda: reader.list_lines(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                rate_card_id="r6b-rate-card-project-a",
                request=RateLineRequest(
                    page_size=25,
                    search="engineer",
                    rate_type="cost",
                    effective_status="current",
                    as_of=date(2026, 8, 28),
                ),
            ),
        )
        assert card_statements == 2
        assert selected_statements == 1
        assert line_statements == 2
        assert cards.total == 2
        assert selected is not None and selected.line_count == 1
        assert lines.total == 1
        assert lines.items[0].rate_amount == Decimal("125.2500")
    finally:
        session.close()


def test_rate_reader_and_direct_child_table_deny_cross_scope(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        reader = SqlAlchemyFinanceRateReader(session=session)
        foreign = reader.list_cards(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            request=RateCardRequest(),
        )
        assert foreign.total == 0
        assert foreign.items == ()
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_rate_cards "
                "WHERE id = 'r6b-rate-card-project-b'"
            )
        ) == 0
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_rate_card_lines "
                "WHERE id = 'r6b-rate-line-project-b'"
            )
        ) == 0
    finally:
        session.close()


def test_rate_reader_postgresql_plans_are_bounded(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        statements = {
            "master": (
                "SELECT c.id, c.name FROM project_finance_rate_cards c "
                "WHERE c.tenant_id = :tenant AND c.organization_id = :organization "
                "AND (c.project_id IS NULL OR c.project_id = :project) "
                "ORDER BY c.name ASC, c.id ASC LIMIT 25"
            ),
            "lines": (
                "SELECT l.id, l.role, l.rate_amount, l.rate_currency "
                "FROM project_finance_rate_card_lines l "
                "JOIN project_finance_rate_cards c ON c.id = l.rate_card_id "
                "WHERE l.tenant_id = :tenant AND l.organization_id = :organization "
                "AND l.rate_card_id = :card "
                "AND c.tenant_id = :tenant AND c.organization_id = :organization "
                "AND (c.project_id IS NULL OR c.project_id = :project) "
                "ORDER BY l.role ASC, l.id ASC LIMIT 25"
            ),
        }
        params = {
            "tenant": TENANT_A,
            "organization": ORG_A,
            "project": PROJECT_A,
            "card": "r6b-rate-card-project-a",
        }
        for name, statement in statements.items():
            rows = session.execute(
                text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {statement}"), params
            ).scalars().all()
            plan = "\n".join(rows)
            assert "Limit" in plan, (name, plan)
            assert "Execution Time" in plan, (name, plan)
    finally:
        session.close()
