from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest
from sqlalchemy import select

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.infrastructure.persistence.orm.audit_entry import AuditEntryORM
from src.core.platform.infrastructure.persistence.orm.auth import UserRoleORM
from src.core.platform.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
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


def _audit_actions(session, membership_id: str) -> list[str]:
    rows = session.execute(
        select(AuditEntryORM)
        .where(AuditEntryORM.entity_type == "tenant_membership")
        .where(AuditEntryORM.entity_id == membership_id)
        .order_by(AuditEntryORM.timestamp)
    ).scalars()
    return [
        str(json.loads(row.metadata_json).get("action") or "")
        for row in rows
    ]


def test_invitation_acceptance_is_self_scoped_atomic_and_one_time(
    services,
    session,
) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test invitation"
    )
    target = _register_user(services, "invitation_target")

    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
    )

    stored = membership_service._membership_repo.get(target.id, tenant_id)
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_INVITED
    assert stored.invitation_token_hash != issued.token
    assert stored.invitation_token_hash == membership_service.hash_invitation_token(
        issued.token
    )

    _set_user_principal(services, target.username)
    accepted = membership_service.accept_invitation(issued.token)

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert accepted.invitation_token_hash is None
    assert membership_service._membership_repo.is_active_member(
        target.id,
        tenant_id,
    )
    viewer = membership_service._role_repo.get_by_name("viewer")
    assert viewer is not None
    active_bindings = (
        membership_service._role_binding_repo.list_active_for_principal(
            target.id,
            tenant_id=tenant_id,
        )
    )
    assert any(binding.role_id == viewer.id for binding in active_bindings)
    assert session.execute(
        select(UserRoleORM.id).where(
            UserRoleORM.user_id == target.id,
            UserRoleORM.role_id == viewer.id,
        )
    ).scalar_one_or_none() is None
    assert _audit_actions(session, accepted.id) == [
        "tenant.membership.invitation_issued",
        "tenant.membership.invitation_accepted",
    ]

    with pytest.raises(BusinessRuleError) as replay_error:
        membership_service.accept_invitation(issued.token)
    assert replay_error.value.code == "TENANT_INVITATION_INVALID"


def test_invitation_cannot_be_accepted_by_another_authenticated_user(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, "invitation_owner")
    other = _register_user(services, "invitation_other")
    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    _set_user_principal(services, other.username)
    with pytest.raises(BusinessRuleError) as mismatch_error:
        membership_service.accept_invitation(issued.token)

    assert mismatch_error.value.code == "TENANT_INVITATION_TARGET_MISMATCH"
    stored = membership_service._membership_repo.get(
        target.id,
        issued.membership.tenant_id,
    )
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_INVITED


def test_revoked_invitation_cannot_be_accepted(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, "revoked_invitation_target")
    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    revoked = membership_service.revoke_invitation(target.id)
    assert revoked.status == MEMBERSHIP_STATUS_REMOVED
    assert revoked.invitation_token_hash is None

    _set_user_principal(services, target.username)
    with pytest.raises(BusinessRuleError) as revoked_error:
        membership_service.accept_invitation(issued.token)
    assert revoked_error.value.code == "TENANT_INVITATION_INVALID"


def test_membership_administration_invalidates_only_affected_sessions(
    services,
    session,
) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_context = services["tenant_context_service"]
    tenant_id = tenant_context.require_active_tenant_id(
        operation_label="test membership administration"
    )
    admin_principal = services["user_session"].principal
    assert admin_principal is not None
    target = _register_user(services, "lifecycle_target")
    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    authenticated = _set_user_principal(services, target.username)
    accepted = membership_service.accept_invitation(issued.token)
    tenant_context.set_active_tenant(tenant_id)
    target_sessions = membership_service._auth_session_repo.list_by_user(
        authenticated.id
    )
    assert any(
        auth_session.last_active_tenant_id == tenant_id
        and auth_session.revoked_at is None
        for auth_session in target_sessions
    )

    services["user_session"].set_principal(admin_principal)
    suspended = membership_service.suspend_member(target.id)
    assert suspended.status == MEMBERSHIP_STATUS_SUSPENDED
    assert all(
        auth_session.revoked_at is not None
        for auth_session in membership_service._auth_session_repo.list_by_user(
            target.id
        )
        if auth_session.last_active_tenant_id == tenant_id
    )

    reactivated = membership_service.reactivate_member(target.id)
    assert reactivated.status == MEMBERSHIP_STATUS_ACTIVE
    removed = membership_service.remove_member(target.id)
    assert removed.status == MEMBERSHIP_STATUS_REMOVED
    assert (
        membership_service._role_binding_repo.list_active_for_principal(
            target.id,
            tenant_id=tenant_id,
        )
        == []
    )
    assert _audit_actions(session, accepted.id) == [
        "tenant.membership.invitation_issued",
        "tenant.membership.invitation_accepted",
        "tenant.membership.suspended",
        "tenant.membership.reactivated",
        "tenant.membership.removed",
    ]


def test_membership_mutation_rolls_back_when_durable_audit_write_fails(
    services,
    monkeypatch,
) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test audit rollback"
    )
    target = _register_user(services, "audit_failure_target")

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        membership_service._audit_repo,
        "add_for_tenant",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        membership_service.issue_invitation(
            target.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

    assert membership_service._membership_repo.get(target.id, tenant_id) is None


def test_acceptance_rolls_back_membership_and_binding_when_audit_fails(
    services,
    monkeypatch,
) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test acceptance rollback"
    )
    target = _register_user(services, "acceptance_audit_failure")
    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    _set_user_principal(services, target.username)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        membership_service._audit_repo,
        "add_for_tenant",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        membership_service.accept_invitation(issued.token)

    stored = membership_service._membership_repo.get(target.id, tenant_id)
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_INVITED
    assert stored.invitation_token_hash is not None
    assert (
        membership_service._role_binding_repo.list_active_for_principal(
            target.id,
            tenant_id=tenant_id,
        )
        == []
    )


def test_membership_administration_requires_permission_and_blocks_self_lockout(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    assert admin_principal is not None
    target = _register_user(services, "unprivileged_target")
    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    _set_user_principal(services, target.username)

    with pytest.raises(BusinessRuleError) as permission_error:
        membership_service.revoke_invitation(target.id)
    assert permission_error.value.code == "PERMISSION_DENIED"

    services["user_session"].set_principal(admin_principal)
    with pytest.raises(BusinessRuleError) as self_lockout_error:
        membership_service.issue_invitation(
            admin_principal.user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    assert self_lockout_error.value.code == "TENANT_MEMBERSHIP_SELF_LOCKOUT"
    assert issued.membership.status == MEMBERSHIP_STATUS_INVITED


def test_invitation_rejects_an_existing_canonical_tenant_member(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test existing canonical member"
    )
    target = services["auth_service"].register_user(
        "ambiguous_role_target",
        _PASSWORD,
        role_names=("planner",),
    )

    with pytest.raises(BusinessRuleError) as membership_error:
        membership_service.issue_invitation(
            target.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

    assert membership_error.value.code == "TENANT_MEMBERSHIP_ALREADY_ACTIVE"
    assert membership_service._membership_repo.is_active_member(
        target.id,
        tenant_id,
    )


def test_invitation_expiry_is_bounded(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, "long_lived_invitation")

    with pytest.raises(BusinessRuleError) as expiry_error:
        membership_service.issue_invitation(
            target.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=31),
        )

    assert expiry_error.value.code == "TENANT_INVITATION_EXPIRY_INVALID"


def test_issuing_invitation_notifies_invitee_without_leaking_the_token(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    notifications = services["notification_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test invitation notification"
    )
    target = _register_user(services, "notified_invitee")

    issued = membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    _set_user_principal(services, target.username)
    mine = notifications.list_my_notifications()
    assert len(mine) == 1
    assert mine[0].category == "tenant.invitation.issued"
    assert issued.token not in mine[0].body
    assert issued.token not in json.dumps(mine[0].metadata)
    assert mine[0].metadata.get("membership_id") == issued.membership.id


def test_revoking_invitation_notifies_invitee(services) -> None:
    membership_service = services["tenant_membership_service"]
    notifications = services["notification_service"]
    target = _register_user(services, "revoke_notified_invitee")
    membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    membership_service.revoke_invitation(target.id)

    _set_user_principal(services, target.username)
    categories = {n.category for n in notifications.list_my_notifications()}
    assert "tenant.invitation.revoked" in categories


def test_list_my_pending_invitations_is_self_scoped_and_excludes_expired(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    owner = _register_user(services, "pending_invitation_owner")
    other = _register_user(services, "pending_invitation_other")
    membership_service.issue_invitation(
        owner.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    _set_user_principal(services, owner.username)
    mine = membership_service.list_my_pending_invitations()
    assert len(mine) == 1
    assert mine[0].user_id == owner.id

    _set_user_principal(services, other.username)
    assert membership_service.list_my_pending_invitations() == []


def test_accept_invitation_for_tenant_requires_no_token(services) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test token-free acceptance"
    )
    target = _register_user(services, "token_free_acceptor")
    membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    _set_user_principal(services, target.username)
    accepted = membership_service.accept_invitation_for_tenant(tenant_id)

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert membership_service._membership_repo.is_active_member(target.id, tenant_id)
    assert membership_service.list_my_pending_invitations() == []


def test_accept_invitation_for_tenant_is_self_scoped(services) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test token-free acceptance self-scope"
    )
    target = _register_user(services, "token_free_owner")
    other = _register_user(services, "token_free_other")
    membership_service.issue_invitation(
        target.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    _set_user_principal(services, other.username)
    with pytest.raises(NotFoundError) as exc:
        membership_service.accept_invitation_for_tenant(tenant_id)
    assert exc.value.code == "TENANT_MEMBERSHIP_NOT_FOUND"


def test_last_effective_tenant_administrator_cannot_be_suspended(
    services,
) -> None:
    membership_service = services["tenant_membership_service"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test last tenant administrator"
    )
    target = services["auth_service"].register_user(
        "last_tenant_admin",
        _PASSWORD,
        role_names=("tenant_admin",),
        tenant_id=tenant_id,
    )
    events = []
    services["user_session"].set_security_denial_listener(events.append)

    with pytest.raises(BusinessRuleError) as last_admin_error:
        membership_service.suspend_member(target.id)

    assert last_admin_error.value.code == "TENANT_LAST_ADMIN_REQUIRED"
    assert membership_service._membership_repo.is_active_member(
        target.id,
        tenant_id,
    )
    assert len(events) == 1
    assert events[0].operation == "authorization.sod.denied"
    assert events[0].reason_code == "TENANT_LAST_ADMIN_REQUIRED"
    assert events[0].target_scope_id == target.id
