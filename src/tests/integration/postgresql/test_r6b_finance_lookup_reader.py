from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_lookup_reader import (
    SqlAlchemyFinanceLookupReader,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role


pytestmark = pytest.mark.postgresql_integration

TENANT_A = "r6b-lookup-tenant-a"
TENANT_B = "r6b-lookup-tenant-b"
ORG_A = "r6b-lookup-org-a"
ORG_B = "r6b-lookup-org-b"
PROJECT_A = "r6b-lookup-project-a"
PROJECT_B = "r6b-lookup-project-b"


def _seed_scope(connection, *, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    project_id = f"r6b-lookup-project-{suffix}"
    code_id = f"r6b-lookup-code-{suffix}"
    connection.execute(
        text(
            "INSERT INTO organizations "
            "(id, tenant_id, organization_code, display_name, timezone_name, base_currency, is_enabled, version) "
            "VALUES (:id, :tenant, :code, :name, 'UTC', 'XAF', true, 1)"
        ),
        {
            "id": organization_id,
            "tenant": tenant_id,
            "code": f"R6B-LKP-{suffix.upper()}",
            "name": f"R6B Lookup {suffix.upper()}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO projects "
            "(id, tenant_id, project_code, name, description, status, organization_id, version) "
            "VALUES (:id, :tenant, :code, :name, '', 'ACTIVE', :organization, 1)"
        ),
        {
            "id": project_id,
            "tenant": tenant_id,
            "code": f"LKP-{suffix.upper()}",
            "name": f"Lookup Project {suffix.upper()}",
            "organization": organization_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_cost_codes "
            "(id, tenant_id, organization_id, code, name, description, is_active, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :code, :name, '', true, 1, :now, :now)"
        ),
        {
            "id": code_id,
            "tenant": tenant_id,
            "organization": organization_id,
            "code": f"LAB-{suffix.upper()}",
            "name": f"Labor {suffix.upper()}",
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_profiles "
            "(id, tenant_id, organization_id, project_id, currency_code, status, billing_method, budget_control_mode, cost_code_policy, is_funded, is_billable, default_cost_code_id, version, created_at, updated_at) "
            "VALUES (:id, :tenant, :organization, :project, 'XAF', 'active', 'non_billable', 'warn', 'restricted', false, false, :code, 1, :now, :now)"
        ),
        {
            "id": f"r6b-lookup-profile-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "project": project_id,
            "code": code_id,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_finance_cost_code_restrictions "
            "(id, tenant_id, organization_id, project_id, cost_code_id, created_at) "
            "VALUES (:id, :tenant, :organization, :project, :code, :now)"
        ),
        {
            "id": f"r6b-lookup-restriction-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "project": project_id,
            "code": code_id,
            "now": now,
        },
    )
    for index in range(3):
        connection.execute(
            text(
                "INSERT INTO tasks "
                "(id, project_id, task_code, wbs_code, sort_order, name, description, status, priority, percent_complete, is_milestone, version) "
                "VALUES (:id, :project, :task_code, :wbs, :sort_order, :name, '', 'TODO', 0, 0, false, 1)"
            ),
            {
                "id": f"r6b-lookup-task-{suffix}-{index}",
                "project": project_id,
                "task_code": f"TSK-{suffix.upper()}-{index}",
                "wbs": str(index + 1),
                "sort_order": index,
                "name": f"Lookup Task {suffix.upper()} {index}",
            },
        )


@pytest.fixture(scope="module", autouse=True)
def seeded_lookup_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in ((TENANT_A, "R6B-LKP-A"), (TENANT_B, "R6B-LKP-B")):
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


def test_finance_lookups_are_bounded_and_rls_scoped_through_runtime_role(
    postgres_test_environment,
) -> None:
    session = postgres_test_environment.runtime_session(
        tenant_id=TENANT_A, organization_id=ORG_A
    )
    try:
        validate_postgresql_execution_role(session)
        reader = SqlAlchemyFinanceLookupReader(session=session)
        projects, project_queries = _count_selects(
            session,
            lambda: reader.search_projects(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                allowed_project_ids=None,
                require_active_finance_profile=True,
                request=FinanceLookupQuery(search="Lookup", page_size=1),
            ),
        )
        tasks, task_queries = _count_selects(
            session,
            lambda: reader.search_tasks(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                request=FinanceLookupQuery(search="Task", page_size=1),
            ),
        )
        codes, code_queries = _count_selects(
            session,
            lambda: reader.search_cost_codes(
                tenant_id=TENANT_A,
                organization_id=ORG_A,
                project_id=PROJECT_A,
                request=ManualActualCostCodeQuery(
                    search="LAB", page_size=1, effective_on=date(2026, 8, 29)
                ),
            ),
        )

        assert (project_queries, task_queries, code_queries) == (2, 2, 2)
        assert projects.total == 1 and projects.items[0].id == PROJECT_A
        assert tasks.total == 3 and len(tasks.items) == 1
        assert codes.total == 1 and codes.items[0].id == "r6b-lookup-code-a"
        assert reader.search_projects(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            allowed_project_ids=None,
            require_active_finance_profile=True,
            request=FinanceLookupQuery(),
        ).total == 0
        assert reader.search_tasks(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            request=FinanceLookupQuery(),
        ).total == 0
        assert reader.search_cost_codes(
            tenant_id=TENANT_B,
            organization_id=ORG_B,
            project_id=PROJECT_B,
            request=ManualActualCostCodeQuery(),
        ).total == 0
    finally:
        session.close()
