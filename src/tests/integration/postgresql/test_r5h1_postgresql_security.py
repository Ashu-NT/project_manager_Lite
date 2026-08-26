from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError

from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
)
from src.infra.persistence.db.optimistic import update_with_version_check
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role
from src.infra.persistence.migrations.helpers.rls_classification import (
    PARENT_SCOPED_RLS_TABLES,
    TENANT_AND_ORGANIZATION_TABLES,
)


pytestmark = pytest.mark.postgresql_integration


SCOPES = {
    "a": ("r5h-tenant-a", "r5h-org-a"),
    "a_other_org": ("r5h-tenant-a", "r5h-org-b"),
    "b": ("r5h-tenant-b", "r5h-org-c"),
}


def _seed_scope(connection, suffix: str, tenant_id: str, organization_id: str) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    connection.execute(
        text(
            "INSERT INTO resources "
            "(id, tenant_id, resource_code, name, kind, role, hourly_rate, is_active, "
            "capacity_percent, cost_type, worker_type, organization_id, version) "
            "VALUES (:id, :tenant, :code, :name, 'PERSON', 'Engineer', 80, true, "
            "100, 'LABOR', 'EXTERNAL', :organization, 1)"
        ),
        {
            "id": f"r5h-resource-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "code": f"R5H-{suffix.upper()}",
            "name": f"R5H Resource {suffix.upper()}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO projects "
            "(id, tenant_id, project_code, name, description, status, organization_id, version) "
            "VALUES (:id, :tenant, :code, :name, '', 'ACTIVE', :organization, 1)"
        ),
        {
            "id": f"r5h-project-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "code": f"R5H-P-{suffix.upper()}",
            "name": f"R5H Project {suffix.upper()}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO tasks "
            "(id, project_id, task_code, wbs_code, sort_order, name, description, status, "
            "priority, percent_complete, is_milestone, version) "
            "VALUES (:id, :project, :code, '1', 1, :name, '', 'TODO', 0, 0, false, 1)"
        ),
        {
            "id": f"r5h-task-{suffix}",
            "project": f"r5h-project-{suffix}",
            "code": f"R5H-T-{suffix.upper()}",
            "name": f"R5H Task {suffix.upper()}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_resources "
            "(id, project_id, resource_id, planned_hours, is_active, version) "
            "VALUES (:id, :project, :resource, 40, true, 1)"
        ),
        {
            "id": f"r5h-project-resource-{suffix}",
            "project": f"r5h-project-{suffix}",
            "resource": f"r5h-resource-{suffix}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO task_assignments "
            "(id, task_id, resource_id, allocation_percent, hours_logged, "
            "allocated_planned_hours, version, project_resource_id, response_status) "
            "VALUES (:id, :task, :resource, 100, 0, 40, 1, :project_resource, 'accepted')"
        ),
        {
            "id": f"r5h-assignment-{suffix}",
            "task": f"r5h-task-{suffix}",
            "resource": f"r5h-resource-{suffix}",
            "project_resource": f"r5h-project-resource-{suffix}",
        },
    )
    connection.execute(
        text(
            "INSERT INTO resource_skills "
            "(id, resource_id, skill_code, skill_name, proficiency, version) "
            "VALUES (:id, :resource, :code, 'PostgreSQL', 'advanced', 1)"
        ),
        {"id": f"r5h-skill-{suffix}", "resource": f"r5h-resource-{suffix}", "code": f"PG-{suffix}"},
    )
    connection.execute(
        text(
            "INSERT INTO resource_certifications "
            "(id, resource_id, certification_code, certification_name, version) "
            "VALUES (:id, :resource, :code, 'R5H Certification', 1)"
        ),
        {"id": f"r5h-cert-{suffix}", "resource": f"r5h-resource-{suffix}", "code": f"CERT-{suffix}"},
    )
    connection.execute(
        text(
            "INSERT INTO task_skill_requirements "
            "(id, task_id, skill_code, validation_mode, version) "
            "VALUES (:id, :task, :code, 'warn', 1)"
        ),
        {"id": f"r5h-requirement-{suffix}", "task": f"r5h-task-{suffix}", "code": f"PG-{suffix}"},
    )
    connection.execute(
        text(
            "INSERT INTO time_entries "
            "(id, tenant_id, organization_id, work_allocation_id, assignment_id, entry_date, "
            "hours, note, owner_type, created_at, updated_at, version) "
            "VALUES (:id, :tenant, :organization, :assignment, :assignment, :entry_date, "
            "8, 'R5H entry', 'work_allocation', :now, :now, 1)"
        ),
        {
            "id": f"r5h-entry-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "assignment": f"r5h-assignment-{suffix}",
            "entry_date": date(2026, 8, 24),
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO timesheet_periods "
            "(id, tenant_id, organization_id, resource_id, period_start, period_end, status, "
            "submitted_at, submitted_by_username, version) "
            "VALUES (:id, :tenant, :organization, :resource, '2026-08-01', '2026-08-31', "
            "'SUBMITTED', :now, 'r5h-user', 1)"
        ),
        {
            "id": f"r5h-period-{suffix}",
            "tenant": tenant_id,
            "organization": organization_id,
            "resource": f"r5h-resource-{suffix}",
            "now": now,
        },
    )


@pytest.fixture(scope="module", autouse=True)
def seeded_security_scopes(postgres_test_environment):
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant_id, code in (("r5h-tenant-a", "R5H-A"), ("r5h-tenant-b", "R5H-B")):
            connection.execute(
                text(
                    "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:id, :code, :name, 'active', true, 1)"
                ),
                {"id": tenant_id, "code": code, "name": code},
            )
        for suffix, (tenant_id, organization_id) in SCOPES.items():
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, tenant_id, organization_code, display_name, timezone_name, base_currency, is_active, version) "
                    "VALUES (:id, :tenant, :code, :name, 'UTC', 'XAF', true, 1)"
                ),
                {
                    "id": organization_id,
                    "tenant": tenant_id,
                    "code": f"R5H-ORG-{suffix.upper()}",
                    "name": f"R5H Organization {suffix}",
                },
            )
            _seed_scope(connection, suffix, tenant_id, organization_id)


def test_runtime_role_is_non_privileged_and_owns_no_application_tables(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=SCOPES["a"][0], organization_id=SCOPES["a"][1]
    )
    try:
        validate_postgresql_execution_role(session)
        row = session.execute(
            text(
                "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
        assert tuple(row) == (False, False)
        owned = session.scalar(
            text(
                "SELECT count(*) FROM pg_tables "
                "WHERE schemaname = 'public' AND tableowner = current_user"
            )
        )
        assert owned == 0
    finally:
        session.close()


def test_r5_tables_have_forced_rls_and_explicit_command_policies(postgres_test_environment):
    protected = set(TENANT_AND_ORGANIZATION_TABLES) | set(PARENT_SCOPED_RLS_TABLES)
    with postgres_test_environment.admin_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = ANY(:tables)"
            ),
            {"tables": sorted(protected)},
        ).all()
        assert {row[0] for row in rows} == protected
        assert all(bool(row[1]) and bool(row[2]) for row in rows)
        commands = connection.execute(
            text(
                "SELECT tablename, cmd FROM pg_policies "
                "WHERE schemaname = 'public' AND tablename = ANY(:tables)"
            ),
            {"tables": sorted(protected)},
        ).all()
    by_table = {table: set() for table in protected}
    for table, command in commands:
        by_table[table].add(command)
    assert all(value == {"SELECT", "INSERT", "UPDATE", "DELETE"} for value in by_table.values())


@pytest.mark.parametrize("scope", ["a", "a_other_org", "b"])
def test_runtime_scope_sees_only_its_resource(postgres_test_environment, scope):
    tenant_id, organization_id = SCOPES[scope]
    session = postgres_test_environment.runtime_session(
        tenant_id=tenant_id, organization_id=organization_id
    )
    try:
        ids = session.scalars(select(text("id")).select_from(text("resources"))).all()
        assert ids == [f"r5h-resource-{scope}"]
    finally:
        session.close()


def test_missing_context_is_deny_safe(postgres_test_environment):
    session = postgres_test_environment.runtime_session(tenant_id=None, organization_id=None)
    try:
        assert session.scalar(text("SELECT count(*) FROM resources")) == 0
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO projects "
                    "(id, tenant_id, project_code, name, description, status, organization_id, version) "
                    "VALUES ('r5h-no-context', 'r5h-tenant-a', 'R5H-NO-CONTEXT', "
                    "'Denied', '', 'ACTIVE', 'r5h-org-a', 1)"
                )
            )
    finally:
        session.rollback()
        session.close()


def test_cross_scope_parent_reads_writes_and_insert_are_denied(postgres_test_environment):
    session = postgres_test_environment.runtime_session(
        tenant_id=SCOPES["a"][0], organization_id=SCOPES["a"][1]
    )
    try:
        assert session.scalar(
            text("SELECT count(*) FROM resources WHERE id = 'r5h-resource-b'")
        ) == 0
        assert session.execute(
            text("UPDATE resources SET name = 'attack' WHERE id = 'r5h-resource-b'")
        ).rowcount == 0
        assert session.execute(
            text("DELETE FROM resources WHERE id = 'r5h-resource-b'")
        ).rowcount == 0
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "INSERT INTO projects "
                    "(id, tenant_id, project_code, name, description, status, organization_id, version) "
                    "VALUES ('r5h-cross-project', 'r5h-tenant-b', 'R5H-CROSS', "
                    "'Denied', '', 'ACTIVE', 'r5h-org-c', 1)"
                )
            )
    finally:
        session.rollback()
        session.close()


@pytest.mark.parametrize(
    ("table", "foreign_row_id", "insert_sql"),
    [
        ("resource_skills", "r5h-skill-b", "INSERT INTO resource_skills (id, resource_id, skill_code, skill_name, proficiency, version) VALUES ('attack-skill', 'r5h-resource-b', 'ATTACK', 'Attack', 'advanced', 1)"),
        ("resource_certifications", "r5h-cert-b", "INSERT INTO resource_certifications (id, resource_id, certification_code, certification_name, version) VALUES ('attack-cert', 'r5h-resource-b', 'ATTACK', 'Attack', 1)"),
        ("project_resources", "r5h-project-resource-b", "INSERT INTO project_resources (id, project_id, resource_id, planned_hours, is_active, version) VALUES ('attack-project-resource', 'r5h-project-b', 'r5h-resource-b', 1, true, 1)"),
        ("tasks", "r5h-task-b", "INSERT INTO tasks (id, project_id, task_code, wbs_code, sort_order, name, description, status, priority, percent_complete, is_milestone, version) VALUES ('attack-task', 'r5h-project-b', 'ATTACK', '99', 99, 'Attack', '', 'TODO', 0, 0, false, 1)"),
        ("task_assignments", "r5h-assignment-b", "INSERT INTO task_assignments (id, task_id, resource_id, allocation_percent, hours_logged, allocated_planned_hours, version, response_status) VALUES ('attack-assignment', 'r5h-task-b', 'r5h-resource-b', 100, 0, 1, 1, 'pending')"),
        ("task_skill_requirements", "r5h-requirement-b", "INSERT INTO task_skill_requirements (id, task_id, skill_code, validation_mode, version) VALUES ('attack-requirement', 'r5h-task-b', 'ATTACK', 'warn', 1)"),
    ],
)
def test_parent_scoped_child_direct_bypass_is_denied(
    postgres_test_environment, table, foreign_row_id, insert_sql
):
    session = postgres_test_environment.runtime_session(
        tenant_id=SCOPES["a"][0], organization_id=SCOPES["a"][1]
    )
    try:
        assert session.scalar(
            text(f'SELECT count(*) FROM "{table}" WHERE id = :id'), {"id": foreign_row_id}
        ) == 0
        with pytest.raises(DBAPIError):
            session.execute(text(insert_sql))
    finally:
        session.rollback()
        session.close()


def test_optimistic_concurrency_runs_through_runtime_role(postgres_test_environment):
    first = postgres_test_environment.runtime_session(
        tenant_id=SCOPES["a"][0], organization_id=SCOPES["a"][1]
    )
    stale = postgres_test_environment.runtime_session(
        tenant_id=SCOPES["a"][0], organization_id=SCOPES["a"][1]
    )
    try:
        first_entry = first.get(TimeEntryORM, "r5h-entry-a")
        stale_entry = stale.get(TimeEntryORM, "r5h-entry-a")
        assert first_entry is not None and stale_entry is not None
        assert first_entry.version == stale_entry.version == 1

        next_version = update_with_version_check(
            first,
            TimeEntryORM,
            "r5h-entry-a",
            1,
            {"hours": 7.5},
            not_found_message="Entry missing.",
            stale_message="Entry changed.",
            extra_filters={"tenant_id": SCOPES["a"][0], "organization_id": SCOPES["a"][1]},
        )
        first.commit()
        assert next_version == 2

        with pytest.raises(ConcurrencyError):
            update_with_version_check(
                stale,
                TimeEntryORM,
                "r5h-entry-a",
                1,
                {"hours": 6.0},
                not_found_message="Entry missing.",
                stale_message="Entry changed.",
                extra_filters={"tenant_id": SCOPES["a"][0], "organization_id": SCOPES["a"][1]},
            )
    finally:
        first.close()
        stale.rollback()
        stale.close()
