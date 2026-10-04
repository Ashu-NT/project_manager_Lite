"""Personal notification RLS, independently of application repository filters."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.postgresql_integration


@pytest.fixture(scope="module")
def notification_rows(postgres_test_environment):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with postgres_test_environment.admin_engine.begin() as connection:
        for tenant in ("r7d-tenant-a", "r7d-tenant-b"):
            connection.execute(text(
                "INSERT INTO tenants (id, tenant_code, display_name, tenant_status, is_active, version) "
                "VALUES (:id, :id, :id, 'active', true, 1)"
            ), {"id": tenant})
        for org, tenant in (
            ("r7d-org-a", "r7d-tenant-a"),
            ("r7d-org-other", "r7d-tenant-a"),
            ("r7d-org-b", "r7d-tenant-b"),
        ):
            connection.execute(text(
                "INSERT INTO organizations "
                "(id, tenant_id, organization_code, display_name, timezone_name, base_currency, status, version) "
                "VALUES (:org, :tenant, :org, :org, 'UTC', 'XAF', 'active', 1)"
            ), {"org": org, "tenant": tenant})
        for user_id in ("r7d-user-a", "r7d-user-other"):
            connection.execute(text(
                "INSERT INTO users (id, username, password_hash, account_type, is_active, created_at, updated_at) "
                "VALUES (:id, :id, 'not-used', 'human', true, :now, :now)"
            ), {"id": user_id, "now": now})
        connection.execute(text(
            "INSERT INTO user_tenants "
            "(id, user_id, tenant_id, status, accepted_at, joined_at, created_at, updated_at) "
            "VALUES ('r7d-member-a', 'r7d-user-a', 'r7d-tenant-a', 'active', "
            ":now, :now, :now, :now)"
        ), {"now": now})
        for row_id, tenant, org, recipient, category in (
            ("r7d-own", "r7d-tenant-a", "r7d-org-a", "r7d-user-a", "pm.task.assigned.v1"),
            ("r7d-other-org", "r7d-tenant-a", "r7d-org-other", "r7d-user-a", "pm.task.assigned.v1"),
            ("r7d-other-tenant", "r7d-tenant-b", "r7d-org-b", "r7d-user-a", "pm.task.assigned.v1"),
            ("r7d-other-user", "r7d-tenant-a", "r7d-org-a", "r7d-user-other", "pm.task.assigned.v1"),
        ):
            connection.execute(text(
                "INSERT INTO notifications "
                "(id, tenant_id, organization_id, recipient_user_id, category, title, body, created_at, metadata_json) "
                "VALUES (:id, :tenant, :org, :recipient, :category, 'Safe', 'Safe body', :now, '{}')"
            ), dict(id=row_id, tenant=tenant, org=org, recipient=recipient, category=category, now=now))


def _identity(session, user_id):
    session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": user_id},
    )


def test_notification_table_has_forced_rls_and_runtime_is_non_owner(postgres_test_environment):
    with postgres_test_environment.runtime_session(tenant_id="r7d-tenant-a", organization_id="r7d-org-a") as session:
        assert session.execute(text(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid='notifications'::regclass"
        )).one() == (True, True)
        assert session.execute(text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
        )).one() == (False, False)
        assert session.scalar(text(
            "SELECT pg_get_userbyid(relowner) = current_user FROM pg_class WHERE oid='notifications'::regclass"
        )) is False


def test_hostile_scope_and_personal_notification_mutation_denied(postgres_test_environment, notification_rows):
    with postgres_test_environment.runtime_session(tenant_id="r7d-tenant-a", organization_id="r7d-org-a") as session:
        _identity(session, "r7d-user-a")
        visible = set(session.scalars(text("SELECT id FROM notifications")))
        assert visible == {"r7d-own"}
        for foreign_id in ("r7d-other-org", "r7d-other-tenant", "r7d-other-user"):
            assert session.execute(text(
                "UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE id=:id"
            ), {"id": foreign_id}).rowcount == 0
        assert session.execute(text(
            "UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE id='r7d-own'"
        )).rowcount == 1
        session.rollback()


def test_notifications_are_not_visible_without_active_tenant(postgres_test_environment, notification_rows):
    with postgres_test_environment.runtime_session(tenant_id=None, organization_id=None) as session:
        _identity(session, "r7d-user-a")
        assert set(session.scalars(text("SELECT id FROM notifications"))) == set()


def test_notification_work_is_tenant_and_org_scoped(postgres_test_environment, notification_rows):
    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO notification_work "
            "(id, tenant_id, organization_id, source_event_id, recipient_user_id, category, title, body, available_at, created_at) "
            "VALUES ('r7d-work-a', 'r7d-tenant-a', 'r7d-org-a', 'event-a', 'r7d-user-a', "
            "'pm.task.assigned.v1', 'Safe', 'Safe', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
            "('r7d-work-b', 'r7d-tenant-b', 'r7d-org-b', 'event-b', 'r7d-user-a', "
            "'pm.task.assigned.v1', 'Safe', 'Safe', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))
    with postgres_test_environment.runtime_session(tenant_id="r7d-tenant-a", organization_id="r7d-org-a") as session:
        assert set(session.scalars(text("SELECT id FROM notification_work"))) == {"r7d-work-a"}


def test_live_runtime_worker_processes_and_replays_once(postgres_test_environment, notification_rows):
    from sqlalchemy.orm import sessionmaker

    from src.core.platform.domain.security.auth.session import UserSessionContext
    from src.infra.integration.notification_dispatcher import NotificationDispatcher
    from src.infra.persistence.db.postgresql_rls import configure_session_rls_context

    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO notification_work "
            "(id, tenant_id, organization_id, source_event_id, recipient_user_id, category, title, body, available_at, created_at) "
            "VALUES ('r7d-work-live', 'r7d-tenant-a', 'r7d-org-other', 'event-live', 'r7d-user-a', "
            "'pm.task.assigned.v1', 'Task assignment', 'Open task if authorized.', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))

    factory = sessionmaker(bind=postgres_test_environment.runtime_engine, future=True)

    def scoped_session():
        session = factory()
        configure_session_rls_context(session, user_session=UserSessionContext())
        return session

    worker = NotificationDispatcher(session_factory=scoped_session)
    assert worker.drain(tenant_id="r7d-tenant-a", organization_id="r7d-org-other") == 1
    assert worker.drain(tenant_id="r7d-tenant-a", organization_id="r7d-org-other") == 0
    with postgres_test_environment.runtime_session(tenant_id="r7d-tenant-a", organization_id="r7d-org-other") as session:
        _identity(session, "r7d-user-a")
        assert session.scalar(text(
            "SELECT count(*) FROM notifications WHERE source_event_id='event-live'"
        )) == 1
        assert session.scalar(text(
            "SELECT status FROM notification_work WHERE id='r7d-work-live'"
        )) == "processed"


def test_two_runtime_workers_produce_one_notification(postgres_test_environment, notification_rows):
    from sqlalchemy.orm import sessionmaker

    from src.core.platform.domain.security.auth.session import UserSessionContext
    from src.infra.integration.notification_dispatcher import NotificationDispatcher
    from src.infra.persistence.db.postgresql_rls import configure_session_rls_context

    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO notification_work "
            "(id, tenant_id, organization_id, source_event_id, recipient_user_id, "
            "category, title, body, available_at, created_at) "
            "VALUES ('r7d-work-race', 'r7d-tenant-a', 'r7d-org-other', "
            "'event-race', 'r7d-user-a', 'pm.task.assigned.v1', "
            "'Task assignment', 'Open task if authorized.', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))

    factory = sessionmaker(bind=postgres_test_environment.runtime_engine, future=True)

    def drain_one():
        def scoped_session():
            session = factory()
            configure_session_rls_context(session, user_session=UserSessionContext())
            return session

        return NotificationDispatcher(session_factory=scoped_session).drain(
            tenant_id="r7d-tenant-a", organization_id="r7d-org-other", limit=1,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: drain_one(), range(2)))
    assert sum(results) == 1
    with postgres_test_environment.runtime_session(
        tenant_id="r7d-tenant-a", organization_id="r7d-org-other",
    ) as session:
        _identity(session, "r7d-user-a")
        assert session.scalar(text(
            "SELECT count(*) FROM notifications WHERE source_event_id='event-race'"
        )) == 1


def test_concurrent_runtime_mark_read_is_idempotent(postgres_test_environment, notification_rows):
    from src.core.platform.infrastructure.persistence.repositories.notifications.notification import (
        SqlAlchemyNotificationRepository,
    )

    with postgres_test_environment.admin_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO notifications "
            "(id, tenant_id, organization_id, recipient_user_id, category, title, "
            "body, created_at, metadata_json) "
            "VALUES ('r7d-read-race', 'r7d-tenant-a', 'r7d-org-other', "
            "'r7d-user-a', 'platform.notice.v1', 'Notice', 'Safe', "
            "CURRENT_TIMESTAMP, '{}')"
        ))

    def mark_once(_):
        with postgres_test_environment.runtime_session(
            tenant_id="r7d-tenant-a", organization_id="r7d-org-other",
        ) as session:
            _identity(session, "r7d-user-a")
            repo = SqlAlchemyNotificationRepository(session)
            repo.mark_read(
                "r7d-read-race", user_id="r7d-user-a",
                tenant_id="r7d-tenant-a", organization_id="r7d-org-other",
                read_at=datetime.now(timezone.utc),
            )
            session.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(mark_once, range(2)))
    with postgres_test_environment.runtime_session(
        tenant_id="r7d-tenant-a", organization_id="r7d-org-other",
    ) as session:
        _identity(session, "r7d-user-a")
        assert session.scalar(text(
            "SELECT read_at IS NOT NULL FROM notifications WHERE id='r7d-read-race'"
        )) is True
