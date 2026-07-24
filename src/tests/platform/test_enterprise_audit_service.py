from __future__ import annotations

import pytest


def _login_admin(services):
    auth = services["auth_service"]
    user_session = services["user_session"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(admin))


def test_enterprise_audit_service_is_available(services):
    assert "enterprise_audit_service" in services
    assert services["enterprise_audit_service"] is not None


def test_enterprise_audit_service_list_recent_returns_list(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    results = eas.list_recent(limit=10)
    assert isinstance(results, list)


def test_enterprise_audit_service_is_append_only(services):
    eas = services["enterprise_audit_service"]
    assert not hasattr(eas, "update")
    assert not hasattr(eas, "delete")


def test_enterprise_audit_entries_have_required_fields(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    entries = eas.list_recent(limit=20)
    for entry in entries:
        assert hasattr(entry, "id")
        assert hasattr(entry, "operation")
        assert hasattr(entry, "entity_type")
        assert hasattr(entry, "entity_id")
        assert hasattr(entry, "severity")


def test_auth_actions_produce_audit_entries(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    auth.register_user("audit_test_user", "TestPass123!", display_name="Audit Test")
    entries = eas.list_recent(limit=50)
    operations = {e.operation for e in entries}
    assert "create" in operations


def test_role_assignment_produces_audit_entry(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    user = auth.register_user("rbac_audit_user", "TestPass123!")
    auth.assign_role(user.id, "team_member")
    entries = eas.list_recent(limit=50)
    operations = {e.operation for e in entries}
    assert "permission_change" in operations


def test_enterprise_audit_list_recent_respects_limit(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    results = eas.list_recent(limit=3)
    assert len(results) <= 3


def test_enterprise_audit_severity_field_values(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    entries = eas.list_recent(limit=50)
    allowed_severities = {"low", "medium", "high", "critical"}
    for entry in entries:
        assert entry.severity in allowed_severities
