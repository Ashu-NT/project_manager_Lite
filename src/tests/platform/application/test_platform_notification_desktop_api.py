from __future__ import annotations

from src.core.platform.api.desktop.events.notifications.notification import (
    PlatformNotificationDesktopApi,
)

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


def _api(services) -> PlatformNotificationDesktopApi:
    return services["platform_notification_desktop_api"]


def test_list_my_notifications_returns_the_current_principals_notifications(services):
    notification_service = services["notification_service"]
    owner = _register_user(services, "desktop_list_owner")
    notification_service.dispatch(
        recipient_user_id=owner.id,
        category="test.event",
        title="Hello",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, owner.username)
    result = _api(services).list_my_notifications()

    assert result.ok is True
    assert len(result.data) == 1
    assert result.data[0].title == "Hello"
    assert result.data[0].is_read is False


def test_count_my_unread_is_exact(services):
    notification_service = services["notification_service"]
    owner = _register_user(services, "desktop_count_owner")
    for index in range(60):
        notification_service.dispatch(
            recipient_user_id=owner.id,
            category="test.event",
            title=f"Item {index}",
            body="Body",
            commit=True,
        )

    _set_user_principal(services, owner.username)
    result = _api(services).count_my_unread()

    assert result.ok is True
    assert result.data == 60


def test_mark_read_marks_the_given_notification_for_the_current_principal(services):
    notification_service = services["notification_service"]
    owner = _register_user(services, "desktop_mark_read_owner")
    notification = notification_service.dispatch(
        recipient_user_id=owner.id,
        category="test.event",
        title="Hello",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, owner.username)
    result = _api(services).mark_read(notification.id)

    assert result.ok is True
    assert result.data.is_read is True


def test_mark_read_for_another_principals_notification_fails(services):
    notification_service = services["notification_service"]
    owner = _register_user(services, "desktop_mark_read_target")
    other = _register_user(services, "desktop_mark_read_other")
    notification = notification_service.dispatch(
        recipient_user_id=owner.id,
        category="test.event",
        title="Hello",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, other.username)
    result = _api(services).mark_read(notification.id)

    assert result.ok is False
    assert result.error.category == "not_found"


def test_mark_all_read_only_affects_the_current_principals_notifications(services):
    notification_service = services["notification_service"]
    owner = _register_user(services, "desktop_mark_all_owner")
    other = _register_user(services, "desktop_mark_all_other")
    for index in range(3):
        notification_service.dispatch(
            recipient_user_id=owner.id,
            category="test.event",
            title=f"Item {index}",
            body="Body",
            commit=True,
        )
    notification_service.dispatch(
        recipient_user_id=other.id,
        category="test.event",
        title="Other's own",
        body="Body",
        commit=True,
    )

    _set_user_principal(services, owner.username)
    result = _api(services).mark_all_read()

    assert result.ok is True
    assert result.data == 3
    assert _api(services).count_my_unread().data == 0

    _set_user_principal(services, other.username)
    assert _api(services).count_my_unread().data == 1
