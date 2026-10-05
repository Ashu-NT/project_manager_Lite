"""Desktop Notifications adapt authenticated, scoped read and read-state commands."""

from src.tests.platform.application.test_notification_service import principal, register, seed


def _api(services):
    return services["platform_notification_desktop_api"]


def test_list_my_notifications_returns_only_current_recipients_rows(services, session):
    owner = register(services, "desktop-list-owner")
    other = register(services, "desktop-list-other")
    seed(session, recipient=owner.id, notification_id="desktop-owner")
    seed(session, recipient=other.id, notification_id="desktop-other")
    principal(services, owner.username)
    result = _api(services).list_my_notifications()
    assert result.ok and len(result.data) == 1
    assert result.data[0].id == "desktop-owner"
    assert not result.data[0].is_read


def test_count_my_unread_is_exact_beyond_preview_limit(services, session):
    owner = register(services, "desktop-count-owner")
    for index in range(60):
        seed(session, recipient=owner.id, notification_id=f"desktop-count-{index}")
    principal(services, owner.username)
    assert _api(services).count_my_unread().data == 60
    assert len(_api(services).list_my_notifications().data) == 50


def test_mark_read_and_mark_all_read_are_personal(services, session):
    owner = register(services, "desktop-mark-owner")
    other = register(services, "desktop-mark-other")
    seed(session, recipient=owner.id, notification_id="desktop-mark-1")
    seed(session, recipient=owner.id, notification_id="desktop-mark-2")
    seed(session, recipient=other.id, notification_id="desktop-mark-foreign")
    principal(services, owner.username)
    assert _api(services).mark_read("desktop-mark-1").data.is_read
    assert _api(services).mark_all_read().data == 1
    assert _api(services).count_my_unread().data == 0
    principal(services, other.username)
    assert _api(services).count_my_unread().data == 1
    result = _api(services).mark_read("desktop-mark-1")
    assert not result.ok and result.error.category == "not_found"
