from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from src.core.platform.auth.application import AuthService
from src.core.platform.auth.domain import ROLE_SCOPE_PLATFORM
from src.core.platform.infrastructure.persistence.orm.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.infrastructure.persistence.orm.auth import UserORM
from src.core.platform.tenancy.domain.tenant import Tenant
from src.infra.composition.repositories import (
    RepositoryBundle,
    build_repository_bundle,
)


_PASSWORD = "StrongPass123!"


def _fail_tenant_audit(services, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("tenant security audit unavailable")

    monkeypatch.setattr(
        services["auth_service"]._security_audit_repo,
        "add_for_tenant",
        _raise,
    )


def _matching_audits(services, *, entity_id: str, action: str):
    rows = services["session"].execute(
        select(AuditEntryORM)
        .where(AuditEntryORM.entity_id == entity_id)
        .order_by(AuditEntryORM.timestamp)
    ).scalars()
    matching = []
    for row in rows:
        metadata = json.loads(row.metadata_json)
        if metadata.get("action") == action:
            matching.append((row, metadata))
    return matching


def _build_bootstrap_auth(
    session,
) -> tuple[AuthService, RepositoryBundle]:
    repositories = build_repository_bundle(session)
    auth = AuthService(
        session=session,
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        permission_repo=repositories.permission_repo,
        user_role_repo=repositories.user_role_repo,
        role_permission_repo=repositories.role_permission_repo,
        role_binding_repo=repositories.role_binding_repo,
        security_audit_repo=repositories.audit_entry_repo,
    )
    return auth, repositories


def test_registration_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="tenant security audit unavailable"):
        services["auth_service"].register_user(
            "atomic-registration-target",
            _PASSWORD,
        )

    assert (
        services["auth_service"]._user_repo.get_by_username(
            "atomic-registration-target"
        )
        is None
    )


def test_tenant_onboarding_rolls_back_user_and_membership_when_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="tenant security audit unavailable"):
        services["auth_service"].onboard_tenant_user(
            username="atomic-onboarding-target",
            raw_password=_PASSWORD,
        )

    assert (
        services["auth_service"]._user_repo.get_by_username(
            "atomic-onboarding-target"
        )
        is None
    )


def test_legacy_role_assignment_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    target = auth.register_user("atomic-role-assignment-target", _PASSWORD)
    role = auth._require_role_by_name("planner")
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="tenant security audit unavailable"):
        auth.assign_role(target.id, role.name)

    assert auth._user_role_repo.exists(target.id, role.id) is False


def test_legacy_role_revocation_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    target = auth.register_user("atomic-role-revocation-target", _PASSWORD)
    role = auth._require_role_by_name("planner")
    auth.assign_role(target.id, role.name)
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="tenant security audit unavailable"):
        auth.revoke_role(target.id, role.name)

    assert auth._user_role_repo.exists(target.id, role.id) is True


def test_explicit_tenant_registration_audits_target_scope_without_secrets(
    services,
) -> None:
    other_tenant = Tenant.create(
        tenant_code="AUDIT-TARGET",
        display_name="Audit Target Tenant",
    )
    services["tenant_admin_service"]._tenant_repo.add(other_tenant)
    services["session"].commit()

    target = services["auth_service"].register_user(
        "explicit-audit-scope-target",
        _PASSWORD,
        tenant_id=other_tenant.id,
    )

    matching = _matching_audits(
        services,
        entity_id=target.id,
        action="user.register",
    )
    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.tenant_id == other_tenant.id
    assert row.organization_id is None
    assert metadata["role_names"] == ["viewer"]
    assert metadata["must_change_password"] is False
    serialized = json.dumps(metadata).lower()
    assert "password_hash" not in serialized
    assert "raw_password" not in serialized
    assert _PASSWORD.lower() not in serialized
    assert "federated_subject" not in serialized


def test_legacy_role_audit_has_target_scope_and_change_semantics(services) -> None:
    auth = services["auth_service"]
    target = auth.register_user("scoped-role-audit-target", _PASSWORD)
    auth.assign_role(target.id, "planner")

    matching = _matching_audits(
        services,
        entity_id=target.id,
        action="role.assign",
    )
    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.tenant_id == services[
        "tenant_context_service"
    ].get_active_tenant_id()
    assert row.organization_id == services[
        "tenant_context_service"
    ].get_active_organization_id()
    assert row.field == "role"
    assert row.old_value is None
    assert row.new_value == "planner"
    assert row.severity == "high"
    assert metadata["target_user_id"] == target.id


def test_bootstrap_user_uses_explicit_platform_system_actor(services) -> None:
    rows = services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.tenant_id.is_(None))
    ).scalars()
    matching = []
    for row in rows:
        metadata = json.loads(row.metadata_json)
        if metadata.get("action") == "bootstrap.user.register":
            matching.append((row, metadata))

    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.organization_id is None
    assert row.actor_type == "system"
    assert row.actor_username == "local_startup"
    assert row.source == "bootstrap"
    assert row.severity == "critical"
    assert metadata["role_names"] == ["admin"]
    assert metadata["must_change_password"] is True


def test_bootstrap_creation_rolls_back_when_system_audit_fails(
    session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth, repositories = _build_bootstrap_auth(session)
    monkeypatch.setenv("PM_ADMIN_PASSWORD", "BootstrapStrong123!")

    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("platform security audit unavailable")

    monkeypatch.setattr(repositories.audit_entry_repo, "add_platform", _raise)

    with pytest.raises(RuntimeError, match="platform security audit unavailable"):
        auth.bootstrap_defaults()

    assert repositories.user_repo.get_by_username("admin") is None
    assert session.scalar(select(func.count()).select_from(UserORM)) == 0
    assert (
        session.scalar(select(func.count()).select_from(AuditEntryORM))
        == 0
    )


def test_bootstrap_role_repair_rolls_back_when_system_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    admin = auth._user_repo.get_by_username("admin")
    admin_role = auth._require_role_by_name("admin")
    assert admin is not None
    binding = auth._role_binding_repo.get_active_for_assignment(
        principal_id=admin.id,
        role_id=admin_role.id,
        tenant_id=None,
        actual_scope_type=ROLE_SCOPE_PLATFORM,
        actual_scope_id=None,
    )
    assert binding is not None
    auth._role_binding_repo.revoke(
        binding.id,
        revoked_at=binding.assigned_at,
    )
    services["session"].commit()

    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("platform security audit unavailable")

    monkeypatch.setattr(auth._security_audit_repo, "add_platform", _raise)

    with pytest.raises(RuntimeError, match="platform security audit unavailable"):
        auth.bootstrap_defaults()

    assert auth._role_binding_repo.get_active_for_assignment(
        principal_id=admin.id,
        role_id=admin_role.id,
        tenant_id=None,
        actual_scope_type=ROLE_SCOPE_PLATFORM,
        actual_scope_id=None,
    ) is None


def test_idempotent_legacy_role_operations_do_not_emit_audit(services) -> None:
    auth = services["auth_service"]
    target = auth.register_user("idempotent-role-audit-target", _PASSWORD)

    auth.assign_role(target.id, "viewer")
    auth.revoke_role(target.id, "planner")

    assert _matching_audits(
        services,
        entity_id=target.id,
        action="role.assign",
    ) == []
    assert _matching_audits(
        services,
        entity_id=target.id,
        action="role.revoke",
    ) == []
