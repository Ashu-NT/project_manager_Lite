from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.infrastructure.persistence.reads.projects.activity_labels import (
    resolve_project_activity_labels,
)
from src.core.platform.contract.read.history.activity_actor_reader import (
    ActivityActorKind,
)
from src.core.platform.infrastructure.persistence.read.history.activity_actor_reader import (
    SqlAlchemyActivityActorReader,
)
from src.core.platform.infrastructure.persistence.repositories.history.activity.activity import (
    SqlAlchemyActivityRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)

pytestmark = pytest.mark.postgresql_integration


def test_explicit_organization_activity_read_restores_runtime_rls_scope(
    postgres_test_environment,
) -> None:
    tenant_a = "r7g-history-tenant-a"
    tenant_b = "r7g-history-tenant-b"
    org_a = "r7g-history-org-a"
    org_b = "r7g-history-org-b"
    org_foreign = "r7g-history-org-foreign"
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant in (tenant_a, tenant_b):
            connection.execute(
                text(
                    "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                    "VALUES (:id, :id, :id, 'active', true, 1)"
                ),
                {"id": tenant},
            )
        for organization, tenant in (
            (org_a, tenant_a), (org_b, tenant_a), (org_foreign, tenant_b)
        ):
            event_time = datetime.now(timezone.utc)
            connection.execute(
                text(
                    "INSERT INTO organizations (id, tenant_id, organization_code, display_name, "
                    "timezone_name, base_currency, status, version) "
                    "VALUES (:id, :tenant, :id, :id, 'UTC', 'XAF', 'active', 1)"
                ),
                {"id": organization, "tenant": tenant},
            )
            connection.execute(
                text(
                    "INSERT INTO activity_entries (id, action, entity_type, entity_id, module, "
                    "tenant_id, organization_id, timestamp, type, human_message) "
                    "VALUES (:id, 'created', 'organization', :entity_id, 'platform', "
                    ":tenant, :org, :timestamp, 'info', :message)"
                ),
                {
                    "id": f"r7g-history-entry-{organization}",
                    "entity_id": organization,
                    "org": organization,
                    "message": organization,
                    "tenant": tenant,
                    "timestamp": event_time,
                },
            )
            if organization == org_b:
                connection.execute(
                    text(
                        "INSERT INTO activity_entries (id, action, entity_type, entity_id, module, "
                        "tenant_id, organization_id, timestamp, type, human_message) "
                        "VALUES (:id, 'updated', 'organization', :entity_id, 'platform', "
                        ":tenant, :org, :timestamp, 'info', :message)"
                    ),
                    {
                        "id": "r7g-history-entry-z",
                        "entity_id": organization,
                        "org": organization,
                        "message": "Second event",
                        "tenant": tenant,
                        "timestamp": event_time,
                    },
                )
            connection.execute(
                text(
                    "INSERT INTO audit_entries "
                    "(id, timestamp, entity_type, entity_id, operation, module, tenant_id, organization_id) "
                    "VALUES (:id, :timestamp, 'organization', :entity_id, 'created', 'platform', "
                    ":tenant, :org)"
                ),
                {
                    "id": f"r7g-history-audit-{organization}",
                    "timestamp": event_time,
                    "entity_id": organization,
                    "tenant": tenant,
                    "org": organization,
                },
            )
        connection.execute(
            text(
                "INSERT INTO audit_entries "
                "(id, timestamp, entity_type, entity_id, operation, module) "
                "VALUES ('r7g-history-platform-audit', :timestamp, 'platform', "
                "'bootstrap', 'created', 'platform')"
            ),
            {"timestamp": datetime.now(timezone.utc)},
        )
        for user_id, tenant in (("r7g-actor-a", tenant_a), ("r7g-actor-b", tenant_b)):
            connection.execute(
                text(
                    "INSERT INTO users (id, username, display_name, password_hash, "
                    "account_type, is_active, created_at, updated_at, version) "
                    "VALUES (:id, :id, :id, 'no-login', 'human', true, :now, :now, 1)"
                ),
                {"id": user_id, "now": datetime.now(timezone.utc)},
            )
            connection.execute(
                text(
                    "INSERT INTO user_tenants "
                    "(id, user_id, tenant_id, status, created_at, updated_at) "
                    "VALUES (:id, :user_id, :tenant_id, 'active', :now, :now)"
                ),
                {
                    "id": f"r7g-membership-{user_id}", "user_id": user_id,
                    "tenant_id": tenant, "now": datetime.now(timezone.utc),
                },
            )

    with postgres_test_environment.runtime_session(
        tenant_id=tenant_a, organization_id=org_a
    ) as session:
        role = session.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
        assert role == (False, False)
        assert session.scalar(
            text(
                "SELECT relowner::regrole::text <> current_user "
                "FROM pg_class WHERE oid = 'activity_entries'::regclass"
            )
        )
        assert session.scalar(
            text("SELECT count(*) FROM activity_entries WHERE organization_id = :org"),
            {"org": org_b},
        ) == 0
        actors = SqlAlchemyActivityActorReader(session).resolve_batch(
            tenant_id=tenant_a, actor_ids=("r7g-actor-a", "r7g-actor-b")
        )
        assert actors["r7g-actor-a"].kind == ActivityActorKind.HUMAN
        assert "r7g-actor-b" not in actors

        _, manager_labels = resolve_project_activity_labels(
            session,
            tenant_id=tenant_a,
            organization_id=org_a,
            entries=((None, {"changes": {"manager_user_id": {
                "from": "r7g-actor-a", "to": "r7g-actor-b",
            }}}),),
        )
        assert manager_labels["user"] == {"r7g-actor-a": "r7g-actor-a"}

        audit_ids = set(session.scalars(text("SELECT id FROM audit_entries")).all())
        assert f"r7g-history-audit-{org_a}" in audit_ids
        assert f"r7g-history-audit-{org_b}" in audit_ids
        assert "r7g-history-platform-audit" in audit_ids
        assert f"r7g-history-audit-{org_foreign}" not in audit_ids

        repository = SqlAlchemyActivityRepository(session)
        repository._context = lambda *, operation_label: SimpleNamespace(
            tenant_id=tenant_a, organization_id=org_a
        )
        rows = repository.list_recent(tenant_id=tenant_a, organization_id=org_b)
        assert [row.id for row in rows] == [
            "r7g-history-entry-z",
            f"r7g-history-entry-{org_b}",
        ]
        page, total, filtered_total = repository.list_page_recent(
            page=1, page_size=25, tenant_id=tenant_a, organization_id=org_b
        )
        assert [row.id for row in page] == [row.id for row in rows]
        assert total == filtered_total == 2
        assert repository.list_recent(
            tenant_id=tenant_a, organization_id=org_foreign
        ) == []
        assert session.scalar(text("SELECT current_setting('app.organization_id')")) == org_a
        assert session.scalar(
            text("SELECT count(*) FROM activity_entries WHERE organization_id = :org"),
            {"org": org_b},
        ) == 0

    with postgres_test_environment.runtime_session(
        tenant_id=None, organization_id=None
    ) as session:
        assert session.scalar(text("SELECT count(*) FROM activity_entries")) == 0
        assert set(session.scalars(text("SELECT id FROM audit_entries")).all()) == {
            "r7g-history-platform-audit"
        }


def test_activity_pages_remain_bounded_as_history_grows(postgres_test_environment) -> None:
    tenant_id = "r7g-volume-tenant"
    organization_id = "r7g-volume-org"
    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
            "VALUES (:id, :id, :id, 'active', true, 1)"
        ), {"id": tenant_id})
        connection.execute(text(
            "INSERT INTO organizations (id, tenant_id, organization_code, display_name, "
            "timezone_name, base_currency, status, version) "
            "VALUES (:id, :tenant, :id, :id, 'UTC', 'XAF', 'active', 1)"
        ), {"id": organization_id, "tenant": tenant_id})

    for lower, upper in ((1, 10), (11, 100), (101, 1000)):
        with postgres_test_environment.admin_engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO activity_entries (id, action, entity_type, entity_id, module, "
                "tenant_id, organization_id, timestamp, type, human_message) "
                "SELECT 'r7g-volume-' || n, 'updated', 'project', 'project-1', "
                "'project_management', :tenant, :org, now(), 'info', 'Project updated' "
                "FROM generate_series(CAST(:lower AS integer), CAST(:upper AS integer)) AS n"
            ), {"tenant": tenant_id, "org": organization_id, "lower": lower, "upper": upper})
            connection.execute(text(
                "INSERT INTO audit_entries "
                "(id, timestamp, entity_type, entity_id, operation, module, tenant_id, organization_id) "
                "SELECT 'r7g-volume-audit-' || n, now(), 'project', 'project-1', "
                "'updated', 'project_management', :tenant, :org "
                "FROM generate_series(CAST(:lower AS integer), CAST(:upper AS integer)) AS n"
            ), {"tenant": tenant_id, "org": organization_id, "lower": lower, "upper": upper})

        with postgres_test_environment.runtime_session(
            tenant_id=tenant_id, organization_id=organization_id
        ) as session:
            repository = SqlAlchemyActivityRepository(session)
            repository._context = lambda *, operation_label: SimpleNamespace(
                tenant_id=tenant_id, organization_id=organization_id
            )
            statements: list[str] = []

            def track(conn, cursor, statement, parameters, context, executemany):
                if "FROM activity_entries" in statement:
                    statements.append(statement)

            event.listen(session.bind, "before_cursor_execute", track)
            try:
                page, total, filtered_total = repository.list_page_recent(
                    page=1, page_size=25, tenant_id=tenant_id,
                    organization_id=organization_id,
                )
            finally:
                event.remove(session.bind, "before_cursor_execute", track)

            assert len(page) == min(upper, 25)
            assert total == filtered_total == upper
            assert len(statements) == 3  # total, filtered count, bounded page
            assert any("LIMIT" in statement.upper() for statement in statements)
            audit_repository = SqlAlchemyAuditRepository(session)
            audit_repository._context = lambda *, operation_label: SimpleNamespace(
                tenant_id=tenant_id, organization_id=organization_id
            )
            audit_rows = audit_repository.list_recent(limit=1000)
            assert len(audit_rows) == min(upper, 100)
            if upper == 1000:
                plan = session.scalars(text(
                    "EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM activity_entries "
                    "WHERE tenant_id = :tenant AND organization_id = :org "
                    "ORDER BY timestamp DESC, id DESC LIMIT 25"
                ), {"tenant": tenant_id, "org": organization_id}).all()
                assert any("Limit" in line for line in plan)
