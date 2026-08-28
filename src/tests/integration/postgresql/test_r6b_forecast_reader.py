from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.financials.models.finance_forecast_facts import (
    ForecastLineRequest,
    ForecastVersionRequest,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_forecast_reader import (
    SqlAlchemyFinanceForecastReader,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6b-forecast-tenant-a"
TENANT_B = "r6b-forecast-tenant-b"
ORG_A = "r6b-forecast-org-a"
ORG_B = "r6b-forecast-org-b"
PROJECT_A = "r6b-forecast-project-a"
PROJECT_B = "r6b-forecast-project-b"


def _seed_scope(connection, *, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    project_id = f"r6b-forecast-project-{suffix}"
    forecast_id = f"r6b-forecast-version-{suffix}"
    cost_code_id = f"r6b-forecast-cost-code-{suffix}"
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
            "code": f"R6B-FC-ORG-{suffix.upper()}",
            "name": f"R6B Forecast Organization {suffix.upper()}",
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
            "code": f"R6B-FC-P-{suffix.upper()}",
            "name": f"R6B Forecast Project {suffix.upper()}",
            "organization": organization_id,
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
            "code": f"R6B-FC-{suffix.upper()}",
            "name": f"Forecast ETC {suffix.upper()}",
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
            "name": f"Forecast {suffix.upper()}",
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_forecast_lines "
            "(id, tenant_id, organization_id, forecast_id, project_id, cost_code_id, "
            "description, amount, currency_code, source_kind, source_type, created_by, "
            "version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :forecast, :project, :cost_code, "
            ":description, 125.2500, 'USD', 'manual', 'manual_estimate', 'r6b', "
            "1, :now, :now)"
        ),
        {
            "id": f"r6b-forecast-line-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "forecast": forecast_id,
            "project": project_id,
            "cost_code": cost_code_id,
            "description": f"Manual replacement ETC {suffix.upper()}",
            "now": now,
        },
    )


@pytest.fixture(scope="module", autouse=True)
def seeded_forecast_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6B-FC-A"), (TENANT_B, "R6B-FC-B")):
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
    # Start the RLS-scoped transaction before measuring Reader-owned SQL.
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


def test_forecast_reader_is_bounded_through_runtime_rls_role(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinanceForecastReader(session=session)

        versions, version_statements = _count_selects(
            session,
            lambda: reader.list_versions(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                request=ForecastVersionRequest(
                    page=1,
                    page_size=25,
                    status="approved",
                    generation_mode="manual",
                ),
            ),
        )
        selected, selected_statements = _count_selects(
            session,
            lambda: reader.get_version(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                forecast_id="r6b-forecast-version-a",
            ),
        )
        lines, line_statements = _count_selects(
            session,
            lambda: reader.list_lines(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                forecast_id="r6b-forecast-version-a",
                request=ForecastLineRequest(
                    page=1,
                    page_size=25,
                    search="replacement",
                    source_type="manual_estimate",
                ),
            ),
        )

        assert version_statements == 2
        assert selected_statements == 1
        assert line_statements == 2
        assert versions.total == 1
        assert selected is not None and selected.total_etc == Decimal("125.2500")
        assert lines.total == 1
        assert lines.items[0].description == "Manual replacement ETC A"
    finally:
        session.close()


def test_forecast_reader_and_child_table_deny_cross_scope_access(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        reader = SqlAlchemyFinanceForecastReader(session=session)
        foreign = reader.list_versions(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            request=ForecastVersionRequest(),
        )
        assert foreign.total == 0
        assert foreign.items == ()
        assert session.scalar(
            text(
                "SELECT count(*) FROM project_finance_forecast_lines "
                "WHERE id = 'r6b-forecast-line-b'"
            )
        ) == 0
    finally:
        session.close()


def test_forecast_reader_postgresql_plans_are_inspected(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A,
        organization_id=ORG_A,
    )
    try:
        plans = {}
        statements = {
            "master": (
                "SELECT f.id, f.revision, count(l.id), coalesce(sum(l.amount), 0) "
                "FROM project_finance_forecasts f "
                "LEFT JOIN project_finance_forecast_lines l ON "
                "l.tenant_id = :tenant AND l.organization_id = :organization "
                "AND l.project_id = :project AND l.forecast_id = f.id "
                "WHERE f.tenant_id = :tenant AND f.organization_id = :organization "
                "AND f.project_id = :project GROUP BY f.id, f.revision "
                "ORDER BY f.revision DESC, f.id ASC LIMIT 25"
            ),
            "detail": (
                "SELECT l.id, l.description, l.amount, c.code "
                "FROM project_finance_forecast_lines l "
                "JOIN project_finance_forecasts f ON f.id = l.forecast_id "
                "JOIN project_finance_cost_codes c ON c.id = l.cost_code_id "
                "WHERE l.tenant_id = :tenant AND l.organization_id = :organization "
                "AND l.project_id = :project AND l.forecast_id = :forecast "
                "AND f.tenant_id = :tenant AND f.organization_id = :organization "
                "AND f.project_id = :project "
                "AND c.tenant_id = :tenant AND c.organization_id = :organization "
                "ORDER BY l.description ASC, l.id ASC LIMIT 25"
            ),
        }
        params = {
            "tenant": TENANT_A,
            "organization": ORG_A,
            "project": PROJECT_A,
            "forecast": "r6b-forecast-version-a",
        }
        for name, statement in statements.items():
            plan = session.scalar(
                text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}"),
                params,
            )[0]
            plans[name] = plan
            assert float(plan.get("Execution Time", -1)) >= 0
            assert plan.get("Plan") is not None

        print(
            "R6B_FORECAST_PLAN "
            + " ".join(
                f"{name}_node={plan['Plan']['Node Type']} "
                f"{name}_ms={float(plan['Execution Time']):.3f}"
                for name, plan in plans.items()
            )
        )
    finally:
        session.close()
