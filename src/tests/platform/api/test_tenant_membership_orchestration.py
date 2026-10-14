from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.core.platform.application.tenant.tenancy.invitation_tokens import (
    hash_invitation_token,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
)
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyRoleBindingRepository,
    SqlAlchemyRoleRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)

_PASSWORD = "StrongPass123!"


# `TenantInvitationCommandHandler` holds only a `TenantMembershipUnitOfWorkFactory`, not individual
# repository attributes -- read persisted state back via a fresh repository bound to the shared
# test session, never via a service-internal attribute.
def _membership_repo(services):
    return SqlAlchemyUserTenantMembershipRepository(services["session"])


def _role_repo(services):
    return SqlAlchemyRoleRepository(services["session"])


def _role_binding_repo(services):
    return SqlAlchemyRoleBindingRepository(services["session"])


def _auth_session_repo(services):
    return SqlAlchemyAuthSessionRepository(services["session"])


def _register_user(services, username: str):
    return services["user_registration"].register_user(
        username,
        _PASSWORD,
        display_name=username,
    )


def _set_user_principal(services, username: str):
    user = services["authentication"].authenticate(username, _PASSWORD)
    principal = services["principal_builder"].build(user)
    services["user_session"].set_principal(principal)
    return user


def _audit_actions(session, membership_id: str) -> list[str]:
    rows = session.execute(
        select(AuditEntryORM)
        .where(AuditEntryORM.entity_type == "tenant_membership")
        .where(AuditEntryORM.entity_id == membership_id)
        .order_by(AuditEntryORM.timestamp)
    ).scalars()
    return [str(json.loads(row.metadata_json).get("action") or "") for row in rows]


def test_invitation_acceptance_is_self_scoped_atomic_and_one_time(
    services,
    session,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test invitation"
    )
    target = _register_user(services, "invitation_target")

    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=2),
    )

    stored = _membership_repo(services).get(target.id, tenant_id)
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_INVITED
    assert stored.invitation_token_hash != issued.token
    assert stored.invitation_token_hash == hash_invitation_token(issued.token)

    _set_user_principal(services, target.username)
    accepted = invitation_commands.accept_invitation(issued.token)

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert accepted.invitation_token_hash is None
    assert _membership_repo(services).is_active_member(
        target.id,
        tenant_id,
    )
    viewer = _role_repo(services).get_by_name("viewer")
    assert viewer is not None
    active_bindings = _role_binding_repo(services).list_active_for_principal(
        target.id,
        tenant_id=tenant_id,
    )
    assert any(binding.role_id == viewer.id for binding in active_bindings)
    assert _audit_actions(session, accepted.id) == [
        "tenant.membership.invitation_issued",
        "tenant.membership.invitation_accepted",
    ]

    with pytest.raises(BusinessRuleError) as replay_error:
        invitation_commands.accept_invitation(issued.token)
    assert replay_error.value.code == "TENANT_INVITATION_INVALID"


def test_invitation_cannot_be_accepted_by_another_authenticated_user(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    target = _register_user(services, "invitation_owner")
    other = _register_user(services, "invitation_other")
    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    _set_user_principal(services, other.username)
    with pytest.raises(BusinessRuleError) as mismatch_error:
        invitation_commands.accept_invitation(issued.token)

    assert mismatch_error.value.code == "TENANT_INVITATION_TARGET_MISMATCH"
    stored = _membership_repo(services).get(
        target.id,
        issued.membership.tenant_id,
    )
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_INVITED


def test_revoked_invitation_cannot_be_accepted(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    target = _register_user(services, "revoked_invitation_target")
    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    revoked = invitation_commands.revoke_invitation(target.id)
    assert revoked.status == MEMBERSHIP_STATUS_REMOVED
    assert revoked.invitation_token_hash is None

    _set_user_principal(services, target.username)
    with pytest.raises(BusinessRuleError) as revoked_error:
        invitation_commands.accept_invitation(issued.token)
    assert revoked_error.value.code == "TENANT_INVITATION_INVALID"


def test_membership_administration_invalidates_only_affected_sessions(
    services,
    session,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_context = services["tenant_context_service"]
    tenant_id = tenant_context.require_active_tenant_id(
        operation_label="test membership administration"
    )
    admin_principal = services["user_session"].principal
    assert admin_principal is not None
    target = _register_user(services, "lifecycle_target")
    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    authenticated = _set_user_principal(services, target.username)
    accepted = invitation_commands.accept_invitation(issued.token)
    tenant_context.set_active_tenant(tenant_id)
    target_sessions = _auth_session_repo(services).list_by_user(authenticated.id)
    assert any(
        auth_session.last_active_tenant_id == tenant_id
        and auth_session.revoked_at is None
        for auth_session in target_sessions
    )

    services["user_session"].set_principal(admin_principal)
    suspended = services["tenant_membership_lifecycle_commands"].suspend_member(
        target.id
    )
    assert suspended.status == MEMBERSHIP_STATUS_SUSPENDED
    assert all(
        auth_session.revoked_at is not None
        for auth_session in _auth_session_repo(services).list_by_user(target.id)
        if auth_session.last_active_tenant_id == tenant_id
    )

    reactivated = services["tenant_membership_lifecycle_commands"].reactivate_member(
        target.id
    )
    assert reactivated.status == MEMBERSHIP_STATUS_ACTIVE
    removed = services["tenant_membership_lifecycle_commands"].remove_member(target.id)
    assert removed.status == MEMBERSHIP_STATUS_REMOVED
    assert (
        _role_binding_repo(services).list_active_for_principal(
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
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test audit rollback"
    )
    target = _register_user(services, "audit_failure_target")

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        SqlAlchemyAuditRepository,
        "add_for_tenant",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        invitation_commands.issue_invitation(
            target.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

    assert _membership_repo(services).get(target.id, tenant_id) is None


def test_acceptance_rolls_back_membership_and_binding_when_audit_fails(
    services,
    monkeypatch,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test acceptance rollback"
    )
    target = _register_user(services, "acceptance_audit_failure")
    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    _set_user_principal(services, target.username)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        SqlAlchemyAuditRepository,
        "add_for_tenant",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        invitation_commands.accept_invitation(issued.token)

    stored = _membership_repo(services).get(target.id, tenant_id)
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_INVITED
    assert stored.invitation_token_hash is not None
    assert (
        _role_binding_repo(services).list_active_for_principal(
            target.id,
            tenant_id=tenant_id,
        )
        == []
    )


def test_membership_administration_requires_permission_and_blocks_self_lockout(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    admin_principal = services["user_session"].principal
    assert admin_principal is not None
    target = _register_user(services, "unprivileged_target")
    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    _set_user_principal(services, target.username)

    with pytest.raises(BusinessRuleError) as permission_error:
        invitation_commands.revoke_invitation(target.id)
    assert permission_error.value.code == "PERMISSION_DENIED"

    services["user_session"].set_principal(admin_principal)
    with pytest.raises(BusinessRuleError) as self_lockout_error:
        invitation_commands.issue_invitation(
            admin_principal.user_id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    assert self_lockout_error.value.code == "TENANT_MEMBERSHIP_SELF_LOCKOUT"
    assert issued.membership.status == MEMBERSHIP_STATUS_INVITED


def test_invitation_rejects_an_existing_canonical_tenant_member(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test existing canonical member"
    )
    target = services["user_registration"].register_user(
        "ambiguous_role_target",
        _PASSWORD,
        role_names=("planner",),
    )

    with pytest.raises(BusinessRuleError) as membership_error:
        invitation_commands.issue_invitation(
            target.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

    assert membership_error.value.code == "TENANT_MEMBERSHIP_ALREADY_ACTIVE"
    assert _membership_repo(services).is_active_member(
        target.id,
        tenant_id,
    )


def test_invitation_expiry_is_bounded(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    target = _register_user(services, "long_lived_invitation")

    with pytest.raises(BusinessRuleError) as expiry_error:
        invitation_commands.issue_invitation(
            target.id,
            expires_at=datetime.now(UTC) + timedelta(days=31),
        )

    assert expiry_error.value.code == "TENANT_INVITATION_EXPIRY_INVALID"


def test_issuing_invitation_uses_pending_invitations_not_in_app_notifications(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    notifications = services["notification_queries"]
    target = _register_user(services, "notified_invitee")

    issued = invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    _set_user_principal(services, target.username)
    assert notifications.list_my_notifications() == []
    pending = services["tenant_membership_queries"].list_my_pending_invitations()
    assert [row.id for row in pending] == [issued.membership.id]


def test_revoking_invitation_does_not_create_in_app_notification(services) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    notifications = services["notification_queries"]
    target = _register_user(services, "revoke_notified_invitee")
    invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    invitation_commands.revoke_invitation(target.id)

    _set_user_principal(services, target.username)
    assert notifications.list_my_notifications() == []
    assert services["tenant_membership_queries"].list_my_pending_invitations() == []


def test_list_my_pending_invitations_is_self_scoped_and_excludes_expired(
    services,
) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    owner = _register_user(services, "pending_invitation_owner")
    other = _register_user(services, "pending_invitation_other")
    invitation_commands.issue_invitation(
        owner.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    _set_user_principal(services, owner.username)
    mine = services["tenant_membership_queries"].list_my_pending_invitations()
    assert len(mine) == 1
    assert mine[0].user_id == owner.id

    _set_user_principal(services, other.username)
    assert services["tenant_membership_queries"].list_my_pending_invitations() == []


def test_accept_invitation_for_tenant_requires_no_token(services) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test token-free acceptance"
    )
    target = _register_user(services, "token_free_acceptor")
    invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    _set_user_principal(services, target.username)
    accepted = invitation_commands.accept_invitation_for_tenant(tenant_id)

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert _membership_repo(services).is_active_member(target.id, tenant_id)
    assert services["tenant_membership_queries"].list_my_pending_invitations() == []


def test_accept_invitation_for_tenant_is_self_scoped(services) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test token-free acceptance self-scope"
    )
    target = _register_user(services, "token_free_owner")
    other = _register_user(services, "token_free_other")
    invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    _set_user_principal(services, other.username)
    with pytest.raises(NotFoundError) as exc:
        invitation_commands.accept_invitation_for_tenant(tenant_id)
    assert exc.value.code == "TENANT_MEMBERSHIP_NOT_FOUND"


def test_desktop_adapter_lists_and_accepts_self_scoped_invitation(services) -> None:
    invitation_commands = services["tenant_invitation_commands"]
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test desktop invitation adapter"
    )
    target = _register_user(services, "desktop_invitation_acceptor")
    invitation_commands.issue_invitation(
        target.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    _set_user_principal(services, target.username)
    api = PlatformTenantDesktopApi(
        tenant_admin_queries=services["tenant_admin_queries"],
        tenant_lifecycle_commands=services["tenant_lifecycle_commands"],
        tenant_membership_queries=services["tenant_membership_queries"],
        tenant_context_service=services["tenant_context_service"],
        tenant_invitation_commands=invitation_commands,
    )

    pending = api.list_pending_invitations()
    accepted = api.accept_invitation(tenant_id)

    assert pending.ok is True
    assert pending.data is not None and len(pending.data) == 1
    assert pending.data[0].tenant_id == tenant_id
    assert pending.data[0].status == MEMBERSHIP_STATUS_INVITED
    assert accepted.ok is True
    assert accepted.data is not None
    assert accepted.data.status == MEMBERSHIP_STATUS_ACTIVE


def test_last_effective_tenant_administrator_cannot_be_suspended(
    services,
) -> None:
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test last tenant administrator"
    )
    target = services["user_registration"].register_user(
        "last_tenant_admin",
        _PASSWORD,
        role_names=("tenant_admin",),
        tenant_id=tenant_id,
    )
    events = []
    services["user_session"].set_security_denial_listener(events.append)

    with pytest.raises(BusinessRuleError) as last_admin_error:
        services["tenant_membership_lifecycle_commands"].suspend_member(target.id)

    assert last_admin_error.value.code == "TENANT_LAST_ADMIN_REQUIRED"
    assert _membership_repo(services).is_active_member(
        target.id,
        tenant_id,
    )
    assert len(events) == 1
    assert events[0].operation == "authorization.sod.denied"
    assert events[0].reason_code == "TENANT_LAST_ADMIN_REQUIRED"
    assert events[0].target_scope_id == target.id
