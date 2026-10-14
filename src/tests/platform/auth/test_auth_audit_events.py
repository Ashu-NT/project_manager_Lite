from __future__ import annotations

from sqlalchemy import select

from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)


def _login_admin(services):
    user_session = services["user_session"]
    admin = services["authentication"].authenticate("admin", "ChangeMe123!")
    user_session.set_principal(services["principal_builder"].build(admin))


def _get_recent_audit_operations(services, limit: int = 50) -> list[str]:
    rows = services["session"].execute(
        select(AuditEntryORM.operation)
        .order_by(AuditEntryORM.timestamp.desc())
        .limit(limit)
    ).scalars()
    return list(rows)


def _register_tenant_identity(services, username: str):
    tenant_id = services[
        "tenant_context_service"
    ].require_active_tenant_id(operation_label="test role audit")
    return services["user_registration"].register_user(
        username,
        "TestPass123!",
        role_names=[],
        tenant_id=tenant_id,
    )


def test_register_user_records_high_severity_audit(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    services["user_registration"].register_user("audit_reg_user", "TestPass123!")
    entries = eas.list_recent(limit=50)
    create_entries = [e for e in entries if e.operation == "create" and e.entity_type == "user"]
    assert len(create_entries) >= 1
    assert all(e.severity == "high" for e in create_entries)


def test_assign_role_records_permission_change(services):
    _login_admin(services)
    user = _register_tenant_identity(services, "role_assign_user")
    services["role_assignment_commands"].assign_role(user.id, "team_member")
    assert "permission_change" in _get_recent_audit_operations(services)


def test_revoke_role_records_delete_operation(services):
    _login_admin(services)
    user = _register_tenant_identity(services, "role_revoke_user")
    services["role_assignment_commands"].assign_role(user.id, "team_member")
    services["role_assignment_commands"].revoke_role(user.id, "team_member")
    operations = _get_recent_audit_operations(services)
    assert "delete" in operations


def test_set_user_active_records_update_audit(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    user = services["user_registration"].register_user("deactivate_user", "TestPass123!")
    services["user_administration_commands"].set_user_active(user.id, False)
    entries = eas.list_recent(limit=50)
    update_entries = [e for e in entries if e.operation == "update" and e.entity_type == "user"]
    assert len(update_entries) >= 1


def test_unlock_user_account_records_audit(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    user = services["user_registration"].register_user("lockout_user", "TestPass123!")
    services["user_administration_commands"].unlock_user_account(user.id)
    entries = eas.list_recent(limit=50)
    update_entries = [e for e in entries if e.operation == "update" and e.entity_type == "user"]
    assert len(update_entries) >= 1


def test_force_password_reset_records_high_severity(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    user = services["user_registration"].register_user("pw_reset_user", "TestPass123!")
    services["password_commands"].force_user_password_reset(user.id)
    entries = eas.list_recent(limit=50)
    high_entries = [e for e in entries if e.severity == "high" and e.entity_type == "user"]
    assert len(high_entries) >= 1


def test_audit_entries_have_entity_id_set(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    services["user_registration"].register_user("entity_id_check_user", "TestPass123!")
    entries = eas.list_recent(limit=50)
    for entry in entries:
        assert entry.entity_id is not None
        assert str(entry.entity_id).strip() != ""


def test_audit_entries_category_for_user_create(services):
    _login_admin(services)
    eas = services["enterprise_audit_service"]
    services["user_registration"].register_user("category_user", "TestPass123!")
    entries = eas.list_recent(limit=50)
    create_user_entries = [
        e for e in entries
        if e.operation == "create" and e.entity_type == "user"
    ]
    assert any(
        getattr(e, "category", None) == "SECURITY"
        for e in create_user_entries
    )
