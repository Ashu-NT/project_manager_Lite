from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from src.core.platform.domain.security.auth.session import UserSessionContext
from src.infra.persistence.db.postgresql_rls import (
    configure_session_rls_context,
    worker_tenant_scope,
)
from src.infra.persistence.migrations.helpers.postgresql_rls import (
    build_nullable_tenant_audit_rls_enable_statements,
    build_tenant_only_rls_enable_statements,
    build_tenant_organization_rls_enable_statements,
)
from src.infra.persistence.migrations.helpers.rls_classification import (
    ALL_CLASSIFIED_TABLES,
    INTENTIONAL_RLS_EXCLUSION_TABLES,
    NULLABLE_TENANT_AUDIT_TABLES,
    TENANT_AND_ORGANIZATION_TABLES,
    TENANT_ONLY_TABLES,
    validate_rls_classification,
)
from src.infra.persistence.orm import Base


class _FakePostgresConnection:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(self) -> None:
        self.parameters: dict[str, str] | None = None

    def execute(self, _statement, parameters):
        self.parameters = dict(parameters)


def test_transaction_context_uses_authenticated_desktop_scope():
    session = Session()
    user_session = UserSessionContext()
    user_session.set_active_tenant_id("tenant-a")
    user_session.set_active_organization_id("org-a")
    configure_session_rls_context(session, user_session=user_session)

    connection = _FakePostgresConnection()
    listener = session.info["pm_rls_context_listener"]
    listener(session, None, connection)

    assert connection.parameters == {
        "tenant_id": "tenant-a",
        "organization_id": "org-a",
        "user_id": "",
    }


def test_worker_scope_overrides_desktop_scope_and_resets_after_exit():
    session = Session()
    user_session = UserSessionContext()
    user_session.set_active_tenant_id("tenant-desktop")
    user_session.set_active_organization_id("org-desktop")
    configure_session_rls_context(session, user_session=user_session)
    listener = session.info["pm_rls_context_listener"]

    worker_connection = _FakePostgresConnection()
    with worker_tenant_scope(
        tenant_id="tenant-worker",
        organization_id="org-worker",
        actor_user_id="service-user",
    ):
        listener(session, None, worker_connection)
    assert worker_connection.parameters == {
        "tenant_id": "tenant-worker",
        "organization_id": "org-worker",
        "user_id": "service-user",
    }

    desktop_connection = _FakePostgresConnection()
    listener(session, None, desktop_connection)
    assert desktop_connection.parameters["tenant_id"] == "tenant-desktop"


def test_sqlite_transaction_context_is_noop():
    session = Session()
    user_session = UserSessionContext()
    configure_session_rls_context(session, user_session=user_session)
    connection = SimpleNamespace(
        dialect=SimpleNamespace(name="sqlite"),
        execute=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("SQLite must not receive PostgreSQL set_config")
        ),
    )

    session.info["pm_rls_context_listener"](session, None, connection)


def test_every_application_table_has_exactly_one_rls_classification():
    columns_by_table = {
        name: set(table.c.keys()) for name, table in Base.metadata.tables.items()
    }

    validate_rls_classification(Base.metadata.tables, columns_by_table)
    groups = (
        TENANT_AND_ORGANIZATION_TABLES,
        TENANT_ONLY_TABLES,
        NULLABLE_TENANT_AUDIT_TABLES,
        INTENTIONAL_RLS_EXCLUSION_TABLES,
    )
    assert set(Base.metadata.tables) == set(ALL_CLASSIFIED_TABLES)
    assert sum(len(group) for group in groups) == len(ALL_CLASSIFIED_TABLES)


def test_rls_classification_contains_no_maintenance_objects():
    forbidden = ("maintenance", "cmms")
    assert not any(
        marker in table.lower()
        for table in ALL_CLASSIFIED_TABLES
        for marker in forbidden
    )


def test_tenant_organization_policy_sql_is_explicit_and_forced():
    statements = build_tenant_organization_rls_enable_statements(
        "projects", quote=lambda identifier: f'"{identifier}"'
    )

    assert statements[:2] == (
        'ALTER TABLE "projects" ENABLE ROW LEVEL SECURITY',
        'ALTER TABLE "projects" FORCE ROW LEVEL SECURITY',
    )
    assert any("FOR SELECT USING" in statement for statement in statements)
    assert any("FOR INSERT WITH CHECK" in statement for statement in statements)
    assert any("FOR UPDATE" in statement and "WITH CHECK" in statement for statement in statements)
    assert any("FOR DELETE USING" in statement for statement in statements)
    assert all("app.tenant_id" in statement for statement in statements[2:])
    assert all("app.organization_id" in statement for statement in statements[2:])


def test_tenant_only_policy_does_not_require_organization_context():
    statements = build_tenant_only_rls_enable_statements(
        "platform_events", quote=lambda identifier: f'"{identifier}"'
    )

    assert all("app.tenant_id" in statement for statement in statements[2:])
    assert all("app.organization_id" not in statement for statement in statements)


def test_nullable_audit_policy_preserves_platform_rows_exactly():
    statements = build_nullable_tenant_audit_rls_enable_statements(
        "audit_entries", quote=lambda identifier: f'"{identifier}"'
    )

    assert statements[:2] == (
        'ALTER TABLE "audit_entries" ENABLE ROW LEVEL SECURITY',
        'ALTER TABLE "audit_entries" FORCE ROW LEVEL SECURITY',
    )
    assert len(statements) == 3
    assert '"audit_entries_tenant_isolation_or_platform"' in statements[2]
    assert "tenant_id IS NULL" in statements[2]
    assert "app.tenant_id" in statements[2]
    assert "app.organization_id" not in statements[2]
