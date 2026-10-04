"""Committed local work is replay-safe and does not persist partial effects."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
    OrganizationORM,
)
from src.core.platform.infrastructure.persistence.orm.notifications.notification import (
    NotificationORM,
)
from src.core.platform.infrastructure.persistence.orm.notifications.notification_work import (
    NotificationWorkORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification_work import (
    enqueue_notification_work,
)
from src.core.shared.events.view_invalidation import (
    ExactRecipient,
    RecipientScope,
    ViewInvalidationHint,
)
from src.infra.events.in_process_view_invalidation_channel import (
    InProcessViewInvalidationChannel,
)
from src.infra.integration.notification_dispatcher import NotificationDispatcher


def _setup(session, services):
    user = services["auth_service"].register_user(
        "durable-notification-user", "StrongPass123!", display_name="Recipient",
    )
    session.add(TenantORM(
        id="durable-notification-tenant", tenant_code="DURABLE-NOTIFY", display_name="Durable",
    ))
    session.flush()
    session.add(OrganizationORM(
        id="org-one", tenant_id="durable-notification-tenant",
        organization_code="DURABLE-NOTIFY-ORG", display_name="Durable Org",
    ))
    now = datetime.now(timezone.utc)
    session.add(UserTenantORM(
        id="durable-member", user_id=user.id, tenant_id="durable-notification-tenant",
        status="active", accepted_at=now, joined_at=now, created_at=now, updated_at=now,
    ))
    session.commit()
    return user.id


def _enqueue(session, recipient_id, *, event_id="event-1"):
    enqueue_notification_work(
        session, tenant_id="durable-notification-tenant", organization_id=None,
        source_event_id=event_id, recipient_user_id=recipient_id,
        category="platform.notice.v1", title="Notice",
        body="A workspace notice is available.", metadata={"source_id": "source-1"},
    )


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_work_and_notification_are_idempotent_across_fresh_session_replay(services, session):
    recipient = _setup(session, services)
    _enqueue(session, recipient)
    _enqueue(session, recipient)
    session.commit()
    assert _count(session, NotificationWorkORM) == 1
    worker = NotificationDispatcher(session_factory=sessionmaker(bind=session.bind, future=True))
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 1
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    assert _count(session, NotificationORM) == 1
    assert session.scalar(select(NotificationWorkORM.status)) == "processed"
    _enqueue(session, recipient)
    session.commit()
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    assert _count(session, NotificationORM) == 1


def test_rollback_before_business_commit_leaves_no_work_or_notification(services, session):
    recipient = _setup(session, services)
    _enqueue(session, recipient)
    session.rollback()
    worker = NotificationDispatcher(session_factory=sessionmaker(bind=session.bind, future=True))
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    assert _count(session, NotificationWorkORM) == 0
    assert _count(session, NotificationORM) == 0


def test_delivery_emits_only_post_commit_recipient_hint(services, session):
    recipient = _setup(session, services)
    channel = InProcessViewInvalidationChannel()
    own_hints: list[ViewInvalidationHint] = []
    other_hints: list[ViewInvalidationHint] = []
    own = channel.subscribe(ExactRecipient(recipient), own_hints.append)
    other = channel.subscribe(ExactRecipient("other-user"), other_hints.append)

    def delivered(tenant_id, organization_id, recipient_id):
        assert _count(session, NotificationORM) == 1
        channel.notify(ViewInvalidationHint(
            scope=RecipientScope(tenant_id, organization_id, recipient_id),
            category="notification", scope_code="notification",
            entity_type="notification", entity_id=recipient_id,
        ))

    _enqueue(session, recipient)
    session.commit()
    worker = NotificationDispatcher(
        session_factory=sessionmaker(bind=session.bind, future=True),
        on_delivered=delivered,
    )
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 1
    assert len(own_hints) == 1
    assert other_hints == []
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    assert len(own_hints) == 1
    own.dispose()
    other.dispose()


def test_revoked_membership_blocks_pending_org_delivery(services, session):
    recipient = _setup(session, services)
    enqueue_notification_work(
        session, tenant_id="durable-notification-tenant", organization_id="org-one",
        source_event_id="org-event", recipient_user_id=recipient,
        category="pm.task.assigned.v1", title="Task assigned", body="Open the task.",
    )
    member = session.scalar(select(UserTenantORM).where(UserTenantORM.user_id == recipient))
    member.status = "removed"
    member.revoked_at = datetime.now(timezone.utc)
    member.removed_at = member.revoked_at
    session.commit()
    worker = NotificationDispatcher(session_factory=sessionmaker(bind=session.bind, future=True))
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id="org-one") == 0
    session.expire_all()
    assert session.scalar(select(NotificationWorkORM.status)) == "quarantined"
    assert _count(session, NotificationORM) == 0


def test_removed_membership_blocks_tenant_wide_work(services, session):
    recipient = _setup(session, services)
    member = session.scalar(select(UserTenantORM).where(UserTenantORM.user_id == recipient))
    member.status = "removed"
    member.revoked_at = datetime.now(timezone.utc)
    member.removed_at = member.revoked_at
    _enqueue(session, recipient)
    session.commit()
    worker = NotificationDispatcher(session_factory=sessionmaker(bind=session.bind, future=True))
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    session.expire_all()
    assert _count(session, NotificationORM) == 0
    assert session.scalar(select(NotificationWorkORM.status)) == "quarantined"


def test_poison_work_is_quarantined_without_notification(services, session):
    recipient = _setup(session, services)
    _enqueue(session, recipient)
    session.commit()
    work = session.scalar(select(NotificationWorkORM))
    work.metadata_json = "not-json"
    session.commit()
    worker = NotificationDispatcher(session_factory=sessionmaker(bind=session.bind, future=True))
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    session.expire_all()
    assert session.scalar(select(NotificationWorkORM.status)) == "quarantined"
    assert _count(session, NotificationORM) == 0


def test_retryable_insert_failure_preserves_pending_effect(monkeypatch, services, session):
    recipient = _setup(session, services)
    _enqueue(session, recipient)
    session.commit()
    from src.core.platform.infrastructure.persistence.repositories.notifications.notification import (
        SqlAlchemyNotificationRepository,
    )

    original = SqlAlchemyNotificationRepository.add_idempotent
    attempts = 0

    def fail_once(self, notification):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary repository failure")
        return original(self, notification)

    monkeypatch.setattr(SqlAlchemyNotificationRepository, "add_idempotent", fail_once)
    worker = NotificationDispatcher(session_factory=sessionmaker(bind=session.bind, future=True))
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 0
    session.expire_all()
    assert _count(session, NotificationORM) == 0
    work = session.scalar(select(NotificationWorkORM))
    assert work.status == "retry" and work.attempt_count == 1
    work.available_at = datetime.now(timezone.utc)
    session.commit()
    assert worker.drain(tenant_id="durable-notification-tenant", organization_id=None) == 1
    assert _count(session, NotificationORM) == 1


def test_conflicting_event_payload_fails_closed(services, session):
    recipient = _setup(session, services)
    _enqueue(session, recipient)
    with pytest.raises(ValueError, match="different content"):
        enqueue_notification_work(
            session, tenant_id="durable-notification-tenant", organization_id=None,
            source_event_id="event-1", recipient_user_id=recipient,
            category="platform.notice.v1", title="Tampered",
            body="A workspace notice is available.",
            metadata={"source_id": "source-1"},
        )


def test_desktop_read_drains_committed_work_after_simulated_restart(services, session):
    user_id = _setup(session, services)
    _enqueue(session, user_id)
    session.commit()
    auth = services["auth_service"]
    user = auth.authenticate("durable-notification-user", "StrongPass123!")
    services["user_session"].set_principal(auth.build_principal(user))
    services["user_session"].set_active_tenant_id("durable-notification-tenant")
    rows = services["notification_service"].list_my_notifications()
    assert len(rows) == 1 and rows[0].source_event_id == "event-1"
    assert session.scalar(select(NotificationWorkORM.status)) == "processed"


def test_real_invitation_commit_does_not_create_in_app_notification(services, session):
    from datetime import timedelta

    auth = services["auth_service"]
    target = auth.register_user(
        "durable-invitation-target", "StrongPass123!", display_name="Invitee",
    )
    issued = services["tenant_membership_service"].issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    assert issued.token
    assert session.scalar(select(NotificationWorkORM).where(
        NotificationWorkORM.recipient_user_id == target.id,
    )) is None
    assert session.scalar(select(func.count()).select_from(NotificationORM).where(
        NotificationORM.recipient_user_id == target.id,
    )) == 0
    target_account = auth.authenticate(target.username, "StrongPass123!")
    services["user_session"].set_principal(auth.build_principal(target_account))
    assert services["notification_service"].list_my_notifications() == []
