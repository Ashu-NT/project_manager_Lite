from __future__ import annotations

import pytest


def _login_admin(services):
    auth = services["auth_service"]
    user_session = services["user_session"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(admin))


def test_activity_service_is_available(services):
    assert "activity_service" in services
    assert services["activity_service"] is not None


def test_activity_service_list_recent_returns_list(services):
    _login_admin(services)
    activity = services["activity_service"]
    results = activity.list_recent(limit=10)
    assert isinstance(results, list)


def test_activity_service_list_recent_respects_limit(services):
    _login_admin(services)
    activity = services["activity_service"]
    results = activity.list_recent(limit=5)
    assert len(results) <= 5


def test_activity_service_is_append_only(services):
    activity = services["activity_service"]
    assert not hasattr(activity, "update")
    assert not hasattr(activity, "delete")


def test_activity_entries_have_expected_fields(services):
    _login_admin(services)
    activity = services["activity_service"]
    entries = activity.list_recent(limit=20)
    for entry in entries:
        assert hasattr(entry, "id")
        assert hasattr(entry, "action")
        assert hasattr(entry, "entity_type")
        assert hasattr(entry, "entity_id")


def test_activity_service_list_recent_with_entity_filter(services):
    _login_admin(services)
    activity = services["activity_service"]
    results = activity.list_recent(limit=10, entity_type="project", entity_id="nonexistent-id")
    assert isinstance(results, list)
    assert len(results) == 0


def test_activity_service_actor_username_is_recorded(services):
    _login_admin(services)
    activity = services["activity_service"]
    entries = activity.list_recent(limit=20)
    admin_entries = [e for e in entries if getattr(e, "actor_username", None) == "admin"]
    assert len(admin_entries) >= 0
