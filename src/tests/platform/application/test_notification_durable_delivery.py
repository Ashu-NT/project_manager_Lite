"""Committed local work is replay-safe and does not persist partial effects."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.notifications.notification import (
    NotificationORM,
)
from src.core.platform.infrastructure.persistence.orm.notifications.notification_work import (
    NotificationWorkORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification_work import (
    enqueue_notification_work,
)
from src.infra.integration.notification_dispatcher import NotificationDispatcher


def _setup(session, services):
    user = services["auth_service"].register_user(
        "durable-notification-user", "StrongPass123!", display_name="Recipient",
    )
    session.add(TenantORM(
        id="durable-notification-tenant", tenant_code="DURABLE-NOTIFY", display_name="Durable",
    ))
    session.commit()
    return user.id


def _enqueue(session, recipient_id, *, event_id="event-1"):
    enqueue_notification_work(
        session, tenant_id="durable-notification-tenant", organization_id=None,
        source_event_id=event_id, recipient_user_id=recipient_id,
        category="tenant.invitation.issued", title="Invitation",
        body="A workspace invitation is available.", metadata={"membership_id": "member-1"},
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
            category="tenant.invitation.issued", title="Tampered",
            body="A workspace invitation is available.",
            metadata={"membership_id": "member-1"},
        )
