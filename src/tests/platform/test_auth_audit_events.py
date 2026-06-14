from __future__ import annotations

import pytest


def _login_admin(services):
    auth = services["auth_service"]
    user_session = services["user_session"]
    admin = auth.authenticate("admin", "ChangeMe123!")
    user_session.set_principal(auth.build_principal(admin))


def _get_recent_audit_operations(services, limit: int = 50) -> list[str]:
    eas = services["enterprise_audit_service"]
    return [e.operation for e in eas.list_recent(limit=limit)]


def test_register_user_records_high_severity_audit(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    auth.register_user("audit_reg_user", "TestPass123!")
    entries = eas.list_recent(limit=50)
    create_entries = [e for e in entries if e.operation == "create" and e.entity_type == "user"]
    assert len(create_entries) >= 1
    assert all(e.severity == "high" for e in create_entries)


def test_assign_role_records_permission_change(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    user = auth.register_user("role_assign_user", "TestPass123!")
    auth.assign_role(user.id, "team_member")
    entries = eas.list_recent(limit=50)
    perm_change_entries = [e for e in entries if e.operation == "permission_change"]
    assert len(perm_change_entries) >= 1


def test_revoke_role_records_delete_operation(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    user = auth.register_user("role_revoke_user", "TestPass123!")
    auth.assign_role(user.id, "team_member")
    auth.revoke_role(user.id, "team_member")
    operations = _get_recent_audit_operations(services)
    assert "delete" in operations


def test_set_user_active_records_update_audit(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    user = auth.register_user("deactivate_user", "TestPass123!")
    auth.set_user_active(user.id, False)
    entries = eas.list_recent(limit=50)
    update_entries = [e for e in entries if e.operation == "update" and e.entity_type == "user"]
    assert len(update_entries) >= 1


def test_unlock_user_account_records_audit(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    user = auth.register_user("lockout_user", "TestPass123!")
    auth.unlock_user_account(user.id)
    entries = eas.list_recent(limit=50)
    update_entries = [e for e in entries if e.operation == "update" and e.entity_type == "user"]
    assert len(update_entries) >= 1


def test_force_password_reset_records_high_severity(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    user = auth.register_user("pw_reset_user", "TestPass123!")
    auth.force_user_password_reset(user.id)
    entries = eas.list_recent(limit=50)
    high_entries = [e for e in entries if e.severity == "high" and e.entity_type == "user"]
    assert len(high_entries) >= 1


def test_audit_entries_have_entity_id_set(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    auth.register_user("entity_id_check_user", "TestPass123!")
    entries = eas.list_recent(limit=50)
    for entry in entries:
        assert entry.entity_id is not None
        assert str(entry.entity_id).strip() != ""


def test_audit_entries_compliance_tag_for_user_create(services):
    _login_admin(services)
    auth = services["auth_service"]
    eas = services["enterprise_audit_service"]
    auth.register_user("compliance_tag_user", "TestPass123!")
    entries = eas.list_recent(limit=50)
    create_user_entries = [
        e for e in entries
        if e.operation == "create" and e.entity_type == "user"
    ]
    assert any(
        getattr(e, "compliance_tag", None) == "SOC2"
        for e in create_user_entries
    )
