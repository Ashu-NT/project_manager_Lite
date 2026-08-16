from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from src.core.platform.domain.security.auth.session import UserSessionContext
from src.infra.persistence.db.postgresql_rls import (
    configure_session_rls_context,
    worker_tenant_scope,
)
from src.infra.persistence.migrations.versions.h6i7j8k9l0m1_enable_postgresql_tenant_rls import (
    TENANT_RLS_TABLES,
)
from src.infra.persistence.migrations.versions.pfaudit_p04_001_enable_audit_entries_rls import (
    _TABLE as AUDIT_ENTRIES_CUSTOM_RLS_TABLE,
)
from src.infra.persistence.orm import Base


_IDENTITY_BOOTSTRAP_TABLES = {
    "notifications",
    "organizations",
    "role_bindings",
    "role_delegation_policies",
    "roles",
    "user_tenants",
}

# Tables with a bespoke policy (not the generic single-predicate one in
# TENANT_RLS_TABLES) because a plain tenant-match predicate would reject or
# hide their legitimate NULL-tenant rows. See pfaudit_p04_001 for audit_entries.
_CUSTOM_POLICY_TABLES = {AUDIT_ENTRIES_CUSTOM_RLS_TABLE}


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


def test_every_tenant_bearing_table_has_rls_or_explicit_bootstrap_classification():
    tenant_tables = {
        table_name
        for table_name, table in Base.metadata.tables.items()
        if "tenant_id" in table.c
    }

    assert tenant_tables == set(TENANT_RLS_TABLES) | _IDENTITY_BOOTSTRAP_TABLES | _CUSTOM_POLICY_TABLES
