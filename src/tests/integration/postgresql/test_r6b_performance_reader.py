from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingQuery,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_performance_reader import (
    SqlAlchemyFinancePerformanceReader,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6b-performance-tenant-a"
TENANT_B = "r6b-performance-tenant-b"
ORG_A = "r6b-performance-org-a"
ORG_B = "r6b-performance-org-b"
PROJECT_A = "r6b-performance-project-a"
PROJECT_B = "r6b-performance-project-b"


def _seed_scope(connection, *, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
    project_id = f"r6b-performance-project-{suffix}"
    profile_id = f"r6b-performance-profile-{suffix}"
    cost_code_id = f"r6b-performance-cost-code-{suffix}"
    forecast_id = f"r6b-performance-forecast-{suffix}"

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
            "code": f"R6B-PERF-ORG-{suffix.upper()}",
            "name": f"R6B Performance Organization {suffix.upper()}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO projects "
            "(id, tenant_id, project_code, name, description, status, "
            "organization_id, start_date, end_date, version) "
            "VALUES (:id, :tenant, :code, :name, '', 'ACTIVE', :organization, "
            "'2026-07-01', '2026-09-30', 1)"
        ),
        {
            "id": project_id,
            "tenant": tenant_id,
            "code": f"R6B-PERF-P-{suffix.upper()}",
            "name": f"R6B Performance Project {suffix.upper()}",
            "organization": organization_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_profiles "
            "(id, tenant_id, organization_id, project_id, currency_code, status, "
            "billing_method, budget_control_mode, cost_code_policy, is_funded, "
            "is_billable, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :project, 'USD', 'active', "
            "'non_billable', 'warn', 'all_active', false, false, 1, :now, :now)"
        ),
        {
            "id": profile_id,
            "tenant": tenant_id,
            "organization": organization_id,
            "project": project_id,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_cost_codes "
            "(id, tenant_id, organization_id, code, name, description, "
            "is_active, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :code, :name, '', true, 1, :now, :now)"
        ),
        {
            "id": cost_code_id,
            "tenant": tenant_id,
            "organization": organization_id,
            "code": f"R6B-PERF-{suffix.upper()}",
            "name": f"Performance ETC {suffix.upper()}",
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_forecasts "
            "(id, tenant_id, organization_id, project_id, name, currency_code, "
            "as_of_date, generation_mode, created_by, status, revision, version, "
            "approved_by, approved_at, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :project, :name, 'USD', "
            "'2026-08-27', 'manual', 'r6b', 'approved', 1, 1, 'r6b', :now, :now, :now)"
        ),
        {
            "id": forecast_id,
            "tenant": tenant_id,
            "organization": organization_id,
            "project": project_id,
            "name": f"Performance Forecast {suffix.upper()}",
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_forecast_lines "
            "(id, tenant_id, organization_id, forecast_id, project_id, cost_code_id, "
            "description, amount, currency_code, source_kind, source_type, "
            "period_start, period_end, created_by, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :forecast, :project, :cost_code, "
            ":description, 125.2500, 'USD', 'manual', 'manual_estimate', "
            "'2026-08-01', '2026-08-31', 'r6b', 1, :now, :now)"
        ),
        {
            "id": f"r6b-performance-forecast-line-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "forecast": forecast_id,
            "project": project_id,
            "cost_code": cost_code_id,
            "description": f"Performance ETC {suffix.upper()}",
            "now": now,
        },
    )


@pytest.fixture(scope="module", autouse=True)
def seeded_performance_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in (
            (TENANT_A, "R6B-PERF-A"),
            (TENANT_B, "R6B-PERF-B"),
        ):
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

    def before_cursor_execute(_conn, _cursor, statement, _params, _context, _many):
        nonlocal statements
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements += 1

    event.listen(session.get_bind(), "before_cursor_execute", before_cursor_execute)
    try:
        return operation(), statements
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", before_cursor_execute)


def test_performance_reader_is_bounded_through_runtime_rls_role(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinancePerformanceReader(session=session)
        facts, statement_count = _count_selects(
            session,
            lambda: reader.read_cost_phasing(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                query=CostPhasingQuery(
                    date_from=date(2026, 7, 1),
                    date_to=date(2026, 9, 30),
                    granularity="quarter",
                ),
            ),
        )

        assert statement_count == 6
        assert facts is not None
        assert facts.currency_code == "USD"
        assert facts.approved_forecast_id == "r6b-performance-forecast-a"
        assert len(facts.periods) == 1
        assert facts.periods[0].period_key == "2026-Q3"
        assert facts.periods[0].forecast_cost == Decimal("125.2500")
        assert facts.periods[0].exposure == Decimal("125.2500")
    finally:
        session.close()


def test_performance_reader_and_child_tables_deny_cross_scope_access(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        reader = SqlAlchemyFinancePerformanceReader(session=session)
        foreign = reader.read_cost_phasing(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            query=CostPhasingQuery(
                date_from=date(2026, 7, 1),
                date_to=date(2026, 9, 30),
                granularity="month",
            ),
        )
        assert foreign is None
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_profiles "
                "WHERE id = 'r6b-performance-profile-b'"
            )
        ) == 0
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_forecasts "
                "WHERE id = 'r6b-performance-forecast-b'"
            )
        ) == 0
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_forecast_lines "
                "WHERE id = 'r6b-performance-forecast-line-b'"
            )
        ) == 0
    finally:
        session.close()


def test_performance_reader_postgresql_plans_are_inspected(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        params = {
            "tenant": TENANT_A,
            "organization": ORG_A,
            "project": PROJECT_A,
            "forecast": "r6b-performance-forecast-a",
            "date_from": date(2026, 7, 1),
            "date_to": date(2026, 9, 30),
        }
        statements = {
            "project": (
                "SELECT p.id, fp.currency_code FROM projects p "
                "JOIN project_finance_profiles fp ON fp.project_id = p.id "
                "AND fp.tenant_id = p.tenant_id "
                "AND fp.organization_id = p.organization_id "
                "WHERE p.tenant_id = :tenant AND p.organization_id = :organization "
                "AND p.id = :project"
            ),
            "cost_phasing": (
                "SELECT l.id, l.period_start, l.amount, l.currency_code "
                "FROM project_finance_forecast_lines l "
                "JOIN project_finance_forecasts f ON f.id = l.forecast_id "
                "WHERE l.tenant_id = :tenant AND l.organization_id = :organization "
                "AND l.project_id = :project AND l.forecast_id = :forecast "
                "AND (l.period_end IS NULL OR l.period_end >= :date_from) "
                "AND (l.period_start IS NULL OR l.period_start <= :date_to) "
                "ORDER BY l.period_start, l.id"
            ),
        }
        plans = {}
        for name, statement in statements.items():
            plan = session.scalar(
                text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}"),
                params,
            )[0]
            plans[name] = plan
            assert float(plan.get("Execution Time", -1)) >= 0
            assert plan.get("Plan") is not None

        print(
            "R6B_PERFORMANCE_PLAN "
            + " ".join(
                f"{name}_node={plan['Plan']['Node Type']} "
                f"{name}_ms={float(plan['Execution Time']):.3f}"
                for name, plan in plans.items()
            )
        )
    finally:
        session.close()
