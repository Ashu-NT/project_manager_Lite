from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.domain.security.auth.session import UserSessionContext
from src.infra.persistence.db.postgresql_rls import configure_session_rls_context
from src.infra.persistence.migrations.runner import run_migrations


pytestmark = pytest.mark.postgresql_integration

_EXPECTED_DATABASE = "project_manager_r5h"


@dataclass(frozen=True, slots=True)
class PostgresTestEnvironment:
    admin_url: str
    migration_url: str
    runtime_url: str
    admin_engine: Engine
    runtime_engine: Engine

    def runtime_session(
        self,
        *,
        tenant_id: str | None,
        organization_id: str | None,
    ) -> Session:
        user_session = UserSessionContext()
        user_session.set_active_tenant_id(tenant_id)
        user_session.set_active_organization_id(organization_id)
        session = sessionmaker(bind=self.runtime_engine, expire_on_commit=False)()
        configure_session_rls_context(session, user_session=user_session)
        return session


def _url(name: str, default: str) -> str:
    return str(os.environ.get(name, default)).strip()


def _assert_dedicated_database(engine: Engine) -> None:
    with engine.connect() as connection:
        database = connection.scalar(text("SELECT current_database()"))
    if database != _EXPECTED_DATABASE:
        raise RuntimeError(
            "R5H.1 PostgreSQL tests refuse to reset a non-dedicated database: "
            f"expected={_EXPECTED_DATABASE!r}, actual={database!r}."
        )


@pytest.fixture(scope="session")
def postgres_test_environment() -> Iterator[PostgresTestEnvironment]:
    if os.environ.get("PM_RUN_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Set PM_RUN_POSTGRES_INTEGRATION=1 to run live PostgreSQL tests.")

    port = os.environ.get("PM_R5H1_POSTGRES_PORT", "55432")
    admin_url = _url(
        "PM_R5H1_ADMIN_URL",
        f"postgresql+psycopg://r5h_admin:r5h_admin_test_only@127.0.0.1:{port}/{_EXPECTED_DATABASE}",
    )
    migration_url = _url(
        "PM_R5H1_MIGRATION_URL",
        f"postgresql+psycopg://r5h_migrator:r5h_migrator_test_only@127.0.0.1:{port}/{_EXPECTED_DATABASE}",
    )
    runtime_url = _url(
        "PM_R5H1_RUNTIME_URL",
        f"postgresql+psycopg://app_runtime:app_runtime_test_only@127.0.0.1:{port}/{_EXPECTED_DATABASE}",
    )
    admin_engine = create_engine(admin_url, future=True)
    _assert_dedicated_database(admin_engine)

    with admin_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public AUTHORIZATION r5h_migrator"))
        connection.execute(text("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
        connection.execute(text("GRANT USAGE ON SCHEMA public TO app_runtime"))

    run_migrations(migration_url)

    with admin_engine.begin() as connection:
        connection.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                "IN SCHEMA public TO app_runtime"
            )
        )
        connection.execute(
            text(
                "GRANT USAGE, SELECT ON ALL SEQUENCES "
                "IN SCHEMA public TO app_runtime"
            )
        )

    runtime_engine = create_engine(runtime_url, future=True, pool_pre_ping=True)
    environment = PostgresTestEnvironment(
        admin_url=admin_url,
        migration_url=migration_url,
        runtime_url=runtime_url,
        admin_engine=admin_engine,
        runtime_engine=runtime_engine,
    )
    try:
        yield environment
    finally:
        runtime_engine.dispose()
        admin_engine.dispose()

