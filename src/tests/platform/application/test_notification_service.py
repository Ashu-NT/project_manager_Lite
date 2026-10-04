"""Personal notification reads are bounded, scoped and read-state safe."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import event

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.infrastructure.persistence.orm.notifications.notification import (
    NotificationORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)

PASSWORD = "StrongPass123!"
TENANT = "notification-test-tenant"


def register(services, username):
    return services["auth_service"].register_user(username, PASSWORD, display_name=username)


def principal(services, username):
    auth = services["auth_service"]
    user = auth.authenticate(username, PASSWORD)
    services["user_session"].set_principal(auth.build_principal(user))
    services["user_session"].set_active_tenant_id(TENANT)
    return user


def seed(session, *, recipient, notification_id, tenant=TENANT):
    if session.get(TenantORM, tenant) is None:
        session.add(TenantORM(id=tenant, tenant_code=tenant, display_name=tenant))
        session.flush()
    membership_id = f"notification-membership-{recipient}"
    if session.get(UserTenantORM, membership_id) is None:
        now = datetime.now(timezone.utc)
        session.add(UserTenantORM(
            id=membership_id, user_id=recipient, tenant_id=tenant,
            status="active", accepted_at=now, joined_at=now,
            created_at=now, updated_at=now,
        ))
    row = NotificationORM(
        id=notification_id, recipient_user_id=recipient, tenant_id=tenant,
        organization_id=None, source_event_id=None, category="platform.notice.v1",
        title="Notice", body="You have a workspace notice.",
        created_at=datetime(2026, 10, 3, tzinfo=timezone.utc), metadata_json="{}",
    )
    session.add(row)
    session.commit()
    return row


def test_notification_list_is_bounded_and_stably_ordered(services, session):
    user = register(services, "bounded-notifications")
    for index in range(125):
        seed(session, recipient=user.id, notification_id=f"notification-{index:04d}")
    principal(services, user.username)
    notifications = services["notification_service"]
    page = notifications.list_my_notifications(limit=10000)
    assert len(page) == 100
    assert [row.id for row in page] == [f"notification-{index:04d}" for index in range(124, 24, -1)]
    assert notifications.count_my_unread() == 125
    assert notifications.list_my_notifications(limit=0) == []


def test_thousand_notification_read_stays_bounded_and_uses_two_data_queries(
    services, session,
):
    user = register(services, "volume-notifications")
    seed(session, recipient=user.id, notification_id="volume-0000")
    created = datetime(2026, 10, 3, tzinfo=timezone.utc)
    session.add_all(NotificationORM(
        id=f"volume-{index:04d}", recipient_user_id=user.id,
        tenant_id=TENANT, organization_id=None, source_event_id=None,
        category="platform.notice.v1", title="Notice", body="Safe notice",
        created_at=created, metadata_json="{}",
    ) for index in range(1, 1001))
    session.commit()
    from src.core.platform.infrastructure.persistence.repositories.notifications.notification import (
        SqlAlchemyNotificationRepository,
    )

    repo = SqlAlchemyNotificationRepository(session)
    statements = []

    def record(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT") and "FROM notifications" in statement:
            statements.append(statement)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        page = repo.list_for_user(user.id, tenant_id=TENANT, organization_id=None, limit=10000)
        unread = repo.count_unread_for_user(user.id, tenant_id=TENANT, organization_id=None)
    finally:
        event.remove(session.bind, "before_cursor_execute", record)
    assert len(page) == 100
    assert unread == 1001
    assert len(statements) == 2


def test_personal_visibility_excludes_another_recipient(services, session):
    owner = register(services, "notify-owner")
    other = register(services, "notify-other")
    seed(session, recipient=owner.id, notification_id="owner-invitation")
    principal(services, other.username)
    assert services["notification_service"].list_my_notifications() == []
    with pytest.raises(NotFoundError):
        services["notification_service"].mark_read("owner-invitation")


def test_signed_in_user_without_active_tenant_cannot_read_in_app_notifications(services, session):
    owner = register(services, "notify-no-tenant")
    seed(session, recipient=owner.id, notification_id="tenant-notice")
    principal(services, owner.username)
    services["user_session"].set_active_tenant_id(None)
    notifications = services["notification_service"]
    assert notifications.list_my_notifications() == []
    assert notifications.count_my_unread() == 0
    with pytest.raises(NotFoundError):
        notifications.mark_read("tenant-notice")


def test_authentication_is_required(anonymous_services):
    service = anonymous_services["notification_service"]
    with pytest.raises(BusinessRuleError, match="Authentication"):
        service.list_my_notifications()
    with pytest.raises(BusinessRuleError, match="Authentication"):
        service.count_my_unread()


def test_mark_read_and_mark_all_are_idempotent(services, session):
    owner = register(services, "notify-read-owner")
    seed(session, recipient=owner.id, notification_id="read-first")
    seed(session, recipient=owner.id, notification_id="read-second")
    principal(services, owner.username)
    notifications = services["notification_service"]
    assert notifications.count_my_unread() == 2
    assert notifications.mark_read("read-first").is_read
    assert notifications.mark_read("read-first").is_read
    assert notifications.count_my_unread() == 1
    assert notifications.mark_all_read() == 1
    assert notifications.mark_all_read() == 0
    assert notifications.list_my_notifications(unread_only=True) == []


def test_other_organization_is_hidden_by_repository_even_on_sqlite(services, session):
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
        OrganizationORM,
    )
    owner = register(services, "scoped-notification-owner")
    seed(session, recipient=owner.id, notification_id="tenant-notice")
    now = datetime.now(timezone.utc)
    for org in ("a", "b"):
        session.add(OrganizationORM(
            id=f"notification-org-{org}", tenant_id=TENANT,
            organization_code=f"NOTIF-{org}", display_name=org,
            timezone_name="UTC", base_currency="XAF", status="active",
        ))
    session.flush()
    for org in ("a", "b"):
        session.add(NotificationORM(
            id=f"org-{org}-only", recipient_user_id=owner.id, tenant_id=TENANT,
            organization_id=f"notification-org-{org}", category="pm.task.assigned.v1",
            title="Task", body="Open task if authorized.",
            created_at=now, metadata_json="{}",
        ))
    session.commit()
    principal(services, owner.username)
    services["user_session"].set_active_tenant_id(TENANT)
    services["user_session"].set_active_organization_id("notification-org-a")
    notifications = services["notification_service"]
    assert {row.id for row in notifications.list_my_notifications()} == {"tenant-notice", "org-a-only"}
    with pytest.raises(NotFoundError):
        notifications.mark_read("org-b-only")
    assert notifications.mark_all_read() == 2
