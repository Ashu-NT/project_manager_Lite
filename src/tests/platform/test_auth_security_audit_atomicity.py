from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from src.core.platform.auth.application.security_audit import (
    add_atomic_security_audit,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)


_PASSWORD = "StrongPass123!"


class _CapturingAuditRepository:
    def __init__(self) -> None:
        self.platform_entries = []

    def add_for_tenant(self, _entry, _tenant_id: str) -> None:
        raise AssertionError("Tenant audit path must not be used.")

    def add_platform(self, entry) -> None:
        self.platform_entries.append(entry)


def _platform_audit_service(*, role_names: set[str]):
    repository = _CapturingAuditRepository()
    principal = SimpleNamespace(
        user_id="audit-actor",
        username="audit-actor",
        role_names=frozenset(role_names),
        permissions=frozenset({"platform.admin"}),
    )
    service = SimpleNamespace(
        _security_audit_repo=repository,
        _user_session=SimpleNamespace(principal=principal),
        _tenant_context_service=None,
    )
    return service, repository


def _register_target(services, username: str):
    return services["auth_service"].register_user(
        username,
        _PASSWORD,
        role_names=["viewer"],
    )


def _fail_tenant_audit(services, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("security audit unavailable")

    monkeypatch.setattr(
        services["auth_service"]._security_audit_repo,
        "add_for_tenant",
        _raise,
    )


def test_account_status_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _register_target(services, "atomic-status-target")
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="security audit unavailable"):
        services["auth_service"].set_user_active(target.id, False)

    persisted = services["auth_service"]._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.is_active is True


def test_forced_password_reset_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _register_target(services, "atomic-password-target")
    authenticated = services["auth_service"].authenticate(
        target.username,
        _PASSWORD,
    )
    assert authenticated.active_session_id is not None
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="security audit unavailable"):
        services["auth_service"].force_user_password_reset(target.id)

    persisted = services["auth_service"]._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.must_change_password is False
    assert persisted.session_revision == target.session_revision
    persisted_session = services["auth_service"]._auth_session_repo.get(
        authenticated.active_session_id
    )
    assert persisted_session is not None
    assert persisted_session.revoked_at is None


def test_mfa_provisioning_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _register_target(services, "atomic-mfa-target")
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="security audit unavailable"):
        services["auth_service"].provision_mfa_secret(target.id)

    persisted = services["auth_service"]._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.mfa_secret is None
    assert persisted.mfa_enabled is False


def test_federated_link_rolls_back_when_security_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _register_target(services, "atomic-federated-target")
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="security audit unavailable"):
        services["auth_service"].link_federated_identity(
            target.id,
            identity_provider="oidc",
            federated_subject="subject-not-audited",
        )

    persisted = services["auth_service"]._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.identity_provider is None
    assert persisted.federated_subject is None


def test_security_mutation_fails_closed_without_audit_writer(
    services,
) -> None:
    target = _register_target(services, "missing-audit-writer-target")
    services["auth_service"]._security_audit_repo = None

    with pytest.raises(BusinessRuleError) as exc_info:
        services["auth_service"].set_user_active(target.id, False)

    assert exc_info.value.code == "SECURITY_AUDIT_REQUIRED"
    persisted = services["auth_service"]._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.is_active is True


def test_atomic_security_audit_is_explicitly_scoped_and_redacted(
    services,
) -> None:
    target = _register_target(services, "scoped-security-audit-target")

    services["auth_service"].provision_mfa_secret(target.id)

    rows = services["session"].execute(
        select(AuditEntryORM)
        .where(AuditEntryORM.entity_type == "user")
        .where(AuditEntryORM.entity_id == target.id)
        .order_by(AuditEntryORM.timestamp.desc())
    ).scalars()
    matching = []
    for row in rows:
        metadata = json.loads(row.metadata_json)
        if metadata.get("action") == "mfa.provision":
            matching.append((row, metadata))
    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.tenant_id == services[
        "tenant_context_service"
    ].get_active_tenant_id()
    assert row.organization_id == services[
        "tenant_context_service"
    ].get_active_organization_id()
    assert row.compliance_tag == "SOC2"
    assert metadata["outcome"] == "success"
    serialized = json.dumps(metadata).lower()
    assert "secret" not in serialized
    assert "subject" not in serialized


def test_permission_only_principal_cannot_write_platform_security_audit() -> None:
    service, repository = _platform_audit_service(role_names={"viewer"})

    with pytest.raises(BusinessRuleError) as exc_info:
        add_atomic_security_audit(
            service,
            operation="update",
            entity_type="user",
            entity_id="target-user",
            action="user.set_active",
            severity="medium",
        )

    assert exc_info.value.code == "SECURITY_AUDIT_SCOPE_REQUIRED"
    assert repository.platform_entries == []


def test_canonical_platform_operator_writes_platform_security_audit() -> None:
    service, repository = _platform_audit_service(role_names={"admin"})

    add_atomic_security_audit(
        service,
        operation="update",
        entity_type="user",
        entity_id="target-user",
        action="user.set_active",
        severity="medium",
        metadata={
            "action": "caller.override",
            "outcome": "failure",
        },
    )

    assert len(repository.platform_entries) == 1
    entry = repository.platform_entries[0]
    assert entry.tenant_id is None
    assert entry.organization_id is None
    assert entry.metadata["action"] == "user.set_active"
    assert entry.metadata["outcome"] == "success"
