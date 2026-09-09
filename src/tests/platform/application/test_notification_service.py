from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


_PASSWORD = "StrongPass123!"


def _register_user(services, username: str):
    return services["auth_service"].register_user(
        username,
        _PASSWORD,
        display_name=username,
    )


def _set_user_principal(services, username: str):
    auth = services["auth_service"]
    user = auth.authenticate(username, _PASSWORD)
    principal = auth.build_principal(user)
    services["user_session"].set_principal(principal)
    return user


def test_notification_service_is_available(services):
    assert "notification_service" in services
    assert services["notification_service"] is not None


def test_dispatch_persists_notification_and_is_readable_by_recipient(services, session):
    notifications = services["notification_service"]
    recipient = _register_user(services, "notify_recipient")

    notifications.dispatch(
        recipient_user_id=recipient.id,
        category="test.event",
        title="Hello",
        body="You have a new thing.",
        commit=True,
    )

    _set_user_principal(services, recipient.username)
    mine = notifications.list_my_notifications()
    assert len(mine) == 1
    assert mine[0].category == "test.event"
    assert mine[0].is_read is False


def test_list_my_notifications_is_self_scoped(services):
    notifications = services["notification_service"]
    owner = _register_user(services, "notify_owner")
    other = _register_user(services, "notify_other")

    notifications.dispatch(
        recipient_user_id=owner.id,
        category="test.event",
        title="Owner only",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, other.username)
    assert notifications.list_my_notifications() == []


def test_list_my_notifications_requires_authentication(services, anonymous_services):
    notifications = anonymous_services["notification_service"]
    with pytest.raises(BusinessRuleError) as exc:
        notifications.list_my_notifications()
    assert exc.value.code == "AUTHENTICATION_REQUIRED"


def test_mark_read_by_another_user_is_denied(services):
    notifications = services["notification_service"]
    owner = _register_user(services, "mark_read_owner")
    other = _register_user(services, "mark_read_other")

    notification = notifications.dispatch(
        recipient_user_id=owner.id,
        category="test.event",
        title="Owner only",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, other.username)
    with pytest.raises(NotFoundError):
        notifications.mark_read(notification.id)


def test_mark_read_by_owner_persists_read_at(services):
    notifications = services["notification_service"]
    owner = _register_user(services, "mark_read_self")

    notification = notifications.dispatch(
        recipient_user_id=owner.id,
        category="test.event",
        title="Owner only",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, owner.username)
    read = notifications.mark_read(notification.id)
    assert read.is_read is True

    mine_unread_only = notifications.list_my_notifications(unread_only=True)
    assert mine_unread_only == []
    mine_all = notifications.list_my_notifications()
    assert len(mine_all) == 1
    assert mine_all[0].is_read is True


def test_dispatch_requires_recipient(services):
    notifications = services["notification_service"]
    with pytest.raises(BusinessRuleError) as exc:
        notifications.dispatch(
            recipient_user_id="",
            category="test.event",
            title="Hello",
            body="Body",
        )
    assert exc.value.code == "NOTIFICATION_RECIPIENT_REQUIRED"


def test_channel_delivery_failure_does_not_prevent_dispatch(services):
    notifications = services["notification_service"]
    recipient = _register_user(services, "channel_failure_recipient")

    class _ExplodingChannel:
        def send(self, notification):
            raise RuntimeError("channel unavailable")

    notifications._channels.append(_ExplodingChannel())

    notification = notifications.dispatch(
        recipient_user_id=recipient.id,
        category="test.event",
        title="Hello",
        body="Body",
        commit=True,
    )
    assert notification is not None

    _set_user_principal(services, recipient.username)
    assert len(notifications.list_my_notifications()) == 1
