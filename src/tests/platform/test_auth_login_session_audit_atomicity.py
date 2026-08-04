from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)


_PASSWORD = "StrongPass123!"


def _fail_tenant_audit(services, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("authentication audit unavailable")

    monkeypatch.setattr(
        services["auth_service"]._security_audit_repo,
        "add_for_tenant",
        _raise,
    )


def _matching_audits(
    services,
    *,
    action: str,
    actor_id: str | None = None,
    entity_id: str | None = None,
):
    stmt = select(AuditEntryORM).where(AuditEntryORM.operation == action)
    if actor_id is not None:
        stmt = stmt.where(AuditEntryORM.actor_id == actor_id)
    if entity_id is not None:
        stmt = stmt.where(AuditEntryORM.entity_id == entity_id)
    rows = services["session"].execute(
        stmt.order_by(AuditEntryORM.timestamp)
    ).scalars()
    return [(row, json.loads(row.metadata_json)) for row in rows]


def _register_and_authenticate(services, username: str):
    auth = services["auth_service"]
    target = auth.register_user(username, _PASSWORD)
    authenticated = auth.authenticate(username, _PASSWORD)
    assert authenticated.active_session_id is not None
    return target, authenticated.active_session_id


def test_successful_login_rolls_back_user_and_session_when_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    target = auth.register_user("atomic-login-success-target", _PASSWORD)
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(BusinessRuleError) as exc_info:
        auth.authenticate(target.username, _PASSWORD)

    assert exc_info.value.code == "AUTH_AUDIT_UNAVAILABLE"
    assert str(exc_info.value) == (
        "Authentication could not be completed securely. Please try again."
    )
    persisted = auth._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.last_login_at is None
    assert persisted.last_login_auth_method is None
    assert auth._auth_session_repo.list_by_user(target.id) == []


def test_failed_login_preserves_denial_when_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    target = auth.register_user("atomic-login-denial-target", _PASSWORD)
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(ValidationError) as exc_info:
        auth.authenticate(target.username, "WrongPass123!")

    assert exc_info.value.code == "AUTH_FAILED"
    persisted = auth._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.failed_login_attempts == 0
    assert persisted.locked_until is None


def test_failed_login_counters_lockout_and_audit_commit_together(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    monkeypatch.setenv("PM_AUTH_LOCKOUT_ATTEMPTS", "2")
    target = auth.register_user("atomic-lockout-target", _PASSWORD)

    for _attempt in range(2):
        with pytest.raises(ValidationError) as exc_info:
            auth.authenticate(target.username, "WrongPass123!")
        assert exc_info.value.code == "AUTH_FAILED"

    persisted = auth._user_repo.get(target.id)
    assert persisted is not None
    assert persisted.failed_login_attempts == 2
    assert persisted.locked_until is not None

    with pytest.raises(ValidationError) as locked_error:
        auth.authenticate(target.username, _PASSWORD)
    assert locked_error.value.code == "AUTH_LOCKED"

    matching = _matching_audits(
        services,
        action="auth.login.failed",
        actor_id=target.id,
    )
    assert len(matching) == 3
    assert [metadata["reason"] for _row, metadata in matching] == [
        "invalid_credentials",
        "invalid_credentials",
        "locked_out",
    ]
    assert all(metadata["outcome"] == "denied" for _row, metadata in matching)
    assert all(row.tenant_id is not None for row, _metadata in matching)
    serialized = json.dumps([metadata for _row, metadata in matching]).lower()
    assert "wrongpass" not in serialized
    assert _PASSWORD.lower() not in serialized


def test_unknown_user_login_denial_is_platform_scoped(services) -> None:
    with pytest.raises(ValidationError) as exc_info:
        services["auth_service"].authenticate(
            "unknown-login-subject",
            "UnknownPass123!",
        )
    assert exc_info.value.code == "AUTH_FAILED"

    matching = _matching_audits(
        services,
        action="auth.login.failed",
        entity_id="unknown-login-subject",
    )
    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.actor_id is None
    assert row.actor_type == "authentication_subject"
    assert row.actor_username == "unknown-login-subject"
    assert row.tenant_id is None
    assert row.organization_id is None
    assert metadata["reason"] == "invalid_credentials"
    assert "unknownpass" not in json.dumps(metadata).lower()


def test_unknown_user_denial_is_preserved_when_platform_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_args, **_kwargs) -> None:
        raise RuntimeError("platform authentication audit unavailable")

    monkeypatch.setattr(
        services["auth_service"]._security_audit_repo,
        "add_platform",
        _raise,
    )

    with pytest.raises(ValidationError) as exc_info:
        services["auth_service"].authenticate(
            "unknown-audit-failure-subject",
            "UnknownPass123!",
        )

    assert exc_info.value.code == "AUTH_FAILED"
    assert str(exc_info.value) == "Invalid credentials."


def test_unknown_federated_denial_never_records_subject(services) -> None:
    federated_subject = "sensitive-federated-subject"

    with pytest.raises(ValidationError) as exc_info:
        services["auth_service"].authenticate_federated(
            identity_provider="AzureAD",
            federated_subject=federated_subject,
        )
    assert exc_info.value.code == "AUTH_FAILED"

    matching = _matching_audits(
        services,
        action="auth.login.failed",
        entity_id="federated:azuread",
    )
    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.actor_username == "federated:azuread"
    serialized = json.dumps(metadata).lower()
    assert federated_subject not in serialized
    assert metadata["identity_provider"] == "azuread"
    assert metadata["reason"] == "invalid_federated_identity"


def test_successful_login_audit_is_scoped_and_redacted(services) -> None:
    auth = services["auth_service"]
    target = auth.register_user("scoped-login-success-target", _PASSWORD)

    authenticated = auth.authenticate(target.username, _PASSWORD)
    assert authenticated.active_session_id is not None

    matching = _matching_audits(
        services,
        action="auth.login.success",
        actor_id=target.id,
        entity_id=authenticated.active_session_id,
    )
    assert len(matching) == 1
    row, metadata = matching[0]
    assert row.tenant_id is not None
    assert row.actor_type == "authentication_subject"
    assert metadata["outcome"] == "success"
    assert metadata["auth_method"] == "password"
    assert metadata["target_user_id"] == target.id
    serialized = json.dumps(metadata).lower()
    assert "password_hash" not in serialized
    assert _PASSWORD.lower() not in serialized
    assert "federated_subject" not in serialized


def test_session_policy_rolls_back_user_and_live_sessions_on_audit_failure(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    target, session_id = _register_and_authenticate(
        services,
        "atomic-session-policy-target",
    )
    before = auth._user_repo.get(target.id)
    assert before is not None
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="authentication audit unavailable"):
        auth.set_user_session_policy(
            target.id,
            session_timeout_minutes_override=30,
        )

    persisted = auth._user_repo.get(target.id)
    persisted_session = auth._auth_session_repo.get(session_id)
    assert persisted is not None
    assert persisted.session_timeout_minutes_override is None
    assert persisted.session_revision == before.session_revision
    assert persisted_session is not None
    assert persisted_session.revoked_at is None


def test_revoke_all_sessions_rolls_back_on_audit_failure(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    target, session_id = _register_and_authenticate(
        services,
        "atomic-revoke-all-target",
    )
    before = auth._user_repo.get(target.id)
    assert before is not None
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="authentication audit unavailable"):
        auth.revoke_user_sessions(target.id, note="Security review")

    persisted = auth._user_repo.get(target.id)
    persisted_session = auth._auth_session_repo.get(session_id)
    assert persisted is not None
    assert persisted.session_revision == before.session_revision
    assert persisted_session is not None
    assert persisted_session.revoked_at is None


def test_single_session_revocation_rolls_back_on_audit_failure(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    _target, session_id = _register_and_authenticate(
        services,
        "atomic-single-session-target",
    )
    _fail_tenant_audit(services, monkeypatch)

    with pytest.raises(RuntimeError, match="authentication audit unavailable"):
        auth.revoke_session(session_id, note="Compromised device")

    persisted_session = auth._auth_session_repo.get(session_id)
    assert persisted_session is not None
    assert persisted_session.revoked_at is None


def test_session_administration_audit_is_scoped_and_idempotent(services) -> None:
    auth = services["auth_service"]
    target, session_id = _register_and_authenticate(
        services,
        "scoped-session-admin-target",
    )

    auth.revoke_session(session_id, note="Retired device")
    auth.revoke_session(session_id, note="Duplicate request")
    auth.set_user_session_policy(
        target.id,
        session_timeout_minutes_override=45,
    )

    revoke_events = _matching_audits(
        services,
        action="auth.session.revoked",
        entity_id=session_id,
    )
    assert len(revoke_events) == 1
    revoke_row, revoke_metadata = revoke_events[0]
    assert revoke_row.tenant_id is not None
    assert revoke_row.field == "revoked_at"
    assert revoke_metadata["scope"] == "single"
    assert revoke_metadata["note"] == "Retired device"

    policy_events = _matching_audits(
        services,
        action="auth.session.policy.update",
        entity_id=target.id,
    )
    assert len(policy_events) == 1
    policy_row, policy_metadata = policy_events[0]
    assert policy_row.tenant_id == revoke_row.tenant_id
    assert policy_row.field == "session_timeout_minutes_override"
    assert policy_row.old_value is None
    assert policy_row.new_value == "45"
    assert policy_metadata["session_revision"] > (
        policy_metadata["previous_session_revision"]
    )
