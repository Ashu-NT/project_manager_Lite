from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta, timezone

import pytest

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
    TenantMembershipActivated,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.tenant_membership_unit_of_work import (
    SqlAlchemyTenantMembershipUnitOfWork,
)
from src.core.shared.events.domain_event_context import DomainEventContext

_PASSWORD = "StrongPass123!"
_COUNTER = {"n": 0}
_MEMBERSHIP_EVENT_TYPES = (
    TenantMembershipActivated,
    TenantMembershipSuspended,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
)


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _tenant_id(services) -> str:
    tenant_id = services["tenant_context_service"].require_active_tenant_id(
        operation_label="test"
    )
    assert tenant_id is not None
    return tenant_id


def _register_user(services, username: str):
    return services["auth_service"].register_user(username, _PASSWORD, display_name=username)


def _set_user_principal(services, username: str):
    auth = services["auth_service"]
    user = auth.authenticate(username, _PASSWORD)
    principal = auth.build_principal(user)
    services["user_session"].set_principal(principal)
    return user


class _Recorder:
    """Subscribes to every membership + RoleBinding event on the service's own post-commit
    bus and records (event, context) tuples in commit-observed order, so ordering assertions
    reflect what a real subscriber would see -- never a manually re-sorted list."""

    def __init__(self, services) -> None:
        self.events: list[object] = []
        self.contexts: list[DomainEventContext] = []
        bus = services["tenant_membership_service"]._uow_factory._post_commit_bus
        for event_type in (*_MEMBERSHIP_EVENT_TYPES, RoleBindingAssigned, RoleBindingRevoked):
            bus.subscribe(event_type, self._on_event)

    def _on_event(self, event, context) -> None:
        self.events.append(event)
        self.contexts.append(context)

    def types(self) -> list[type]:
        return [type(e) for e in self.events]

    def of(self, event_type: type) -> list[object]:
        return [e for e in self.events if isinstance(e, event_type)]


def _issue_and_accept(services, *, username: str):
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    target = _register_user(services, username)
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    _set_user_principal(services, target.username)
    accepted = membership_service.accept_invitation(issued.token)
    services["user_session"].set_principal(admin_principal)
    return target, accepted


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------


def test_acceptance_records_activated_after_role_binding_assigned(services):
    recorder = _Recorder(services)
    target, accepted = _issue_and_accept(services, username=_unique_code("p5d2-activate"))

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert recorder.types() == [RoleBindingAssigned, TenantMembershipActivated]
    activated = recorder.of(TenantMembershipActivated)[0]
    assert activated.membership_id == accepted.id
    assert activated.tenant_id == accepted.tenant_id
    assert activated.user_id == target.id


def test_accept_invitation_for_tenant_also_records_activated_exactly_once(services):
    membership_service = services["tenant_membership_service"]
    tenant_id = _tenant_id(services)
    target = _register_user(services, _unique_code("p5d2-activate-for-tenant"))
    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    _set_user_principal(services, target.username)
    recorder = _Recorder(services)

    accepted = membership_service.accept_invitation_for_tenant(tenant_id)

    assert recorder.of(TenantMembershipActivated) == [
        e for e in recorder.of(TenantMembershipActivated)
    ]
    assert len(recorder.of(TenantMembershipActivated)) == 1
    assert recorder.of(TenantMembershipActivated)[0].membership_id == accepted.id


def test_issue_invitation_records_no_membership_event(services):
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d2-issue-no-event"))
    recorder = _Recorder(services)

    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    assert recorder.events == []


def test_reinvite_then_accept_records_removed_then_activated_never_reactivated(services):
    """`removed -> reinvite -> invited -> accept` must produce `TenantMembershipRemoved` (from
    the earlier `remove_member`) and `TenantMembershipActivated` (from acceptance) -- never
    `TenantMembershipReactivated`, and `issue_invitation`'s own reinvite branch itself emits
    nothing (per section 25)."""
    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(services, username=_unique_code("p5d2-reinvite"))
    membership_service.remove_member(target.id)

    recorder = _Recorder(services)
    reinvited = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    assert recorder.events == []  # reinvite itself: eventless

    _set_user_principal(services, target.username)
    accepted = membership_service.accept_invitation(reinvited.token)

    assert recorder.types() == [RoleBindingAssigned, TenantMembershipActivated]
    assert TenantMembershipReactivated not in recorder.types()
    assert recorder.of(TenantMembershipActivated)[0].membership_id == accepted.id


# ---------------------------------------------------------------------------
# Suspension / reactivation
# ---------------------------------------------------------------------------


def test_suspend_then_reactivate_records_exactly_those_two_events_and_no_role_binding_events(
    services,
):
    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(services, username=_unique_code("p5d2-suspend-cycle"))
    recorder = _Recorder(services)

    suspended = membership_service.suspend_member(target.id)
    reactivated = membership_service.reactivate_member(target.id)

    assert suspended.status == MEMBERSHIP_STATUS_SUSPENDED
    assert reactivated.status == MEMBERSHIP_STATUS_ACTIVE
    assert recorder.types() == [TenantMembershipSuspended, TenantMembershipReactivated]
    assert recorder.of(RoleBindingAssigned) == []
    assert recorder.of(RoleBindingRevoked) == []
    assert recorder.of(TenantMembershipSuspended)[0].membership_id == suspended.id
    assert recorder.of(TenantMembershipReactivated)[0].membership_id == reactivated.id


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------


def test_removal_records_role_binding_revoked_before_removed(services):
    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(services, username=_unique_code("p5d2-remove"))
    recorder = _Recorder(services)

    removed = membership_service.remove_member(target.id)

    assert removed.status == MEMBERSHIP_STATUS_REMOVED
    assert recorder.types() == [RoleBindingRevoked, TenantMembershipRemoved]
    assert recorder.of(TenantMembershipRemoved)[0].membership_id == removed.id
    assert recorder.of(TenantMembershipRemoved)[0].user_id == target.id


def test_removal_of_suspended_member_also_records_exactly_one_removed(services):
    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(
        services, username=_unique_code("p5d2-remove-suspended")
    )
    membership_service.suspend_member(target.id)
    recorder = _Recorder(services)

    removed = membership_service.remove_member(target.id)

    assert recorder.of(TenantMembershipRemoved) == recorder.of(TenantMembershipRemoved)
    assert len(recorder.of(TenantMembershipRemoved)) == 1
    assert recorder.of(TenantMembershipRemoved)[0].membership_id == removed.id


# ---------------------------------------------------------------------------
# revoke_invitation: the explicit no-event decision (section 3/26)
# ---------------------------------------------------------------------------


def test_revoke_invitation_emits_no_membership_event(services):
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d2-revoke-invite"))
    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    recorder = _Recorder(services)

    revoked = membership_service.revoke_invitation(target.id)

    assert revoked.status == MEMBERSHIP_STATUS_REMOVED  # persisted status only -- not a fact
    assert recorder.events == []


# ---------------------------------------------------------------------------
# No event on invalid transition
# ---------------------------------------------------------------------------


def test_invalid_transition_records_no_membership_event(services):
    """`suspend_member` on a membership that is still `invited` (never accepted) hits the
    aggregate's own `USER_TENANT_MEMBERSHIP_SUSPEND_INVALID_TRANSITION` guard -- command
    invocation is not the same as a real business transition, so it must record nothing."""
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d2-invalid-transition"))
    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    recorder = _Recorder(services)

    with pytest.raises(BusinessRuleError) as exc:
        membership_service.suspend_member(target.id)
    assert exc.value.code == "USER_TENANT_MEMBERSHIP_SUSPEND_INVALID_TRANSITION"

    assert recorder.events == []


# ---------------------------------------------------------------------------
# Post-commit-only observability / failure isolation
# ---------------------------------------------------------------------------


def test_audit_failure_leaves_zero_observable_membership_event(services, monkeypatch):
    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(
        services, username=_unique_code("p5d2-audit-fail-suspend")
    )
    recorder = _Recorder(services)

    def _fail_audit(self, entry, tenant_id):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(SqlAlchemyAuditRepository, "add_for_tenant", _fail_audit)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        membership_service.suspend_member(target.id)

    assert recorder.events == []


def test_commit_failure_leaves_zero_observable_membership_event(services, monkeypatch):
    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(
        services, username=_unique_code("p5d2-commit-fail-suspend")
    )
    recorder = _Recorder(services)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyTenantMembershipUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        membership_service.suspend_member(target.id)

    assert recorder.events == []


def test_transactional_handler_failure_rolls_back_the_whole_membership_transaction(
    services, monkeypatch
):
    """A FAIL_FAST pre-commit handler failing for `TenantMembershipActivated` must roll back the
    membership transition itself, atomically with the default RoleBinding grant that already
    recorded its own event earlier in the same transaction."""
    membership_service = services["tenant_membership_service"]
    tenant_id = _tenant_id(services)
    target = _register_user(services, _unique_code("p5d2-transactional-fail"))
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    _set_user_principal(services, target.username)

    dispatcher = membership_service._uow_factory._transactional_dispatcher

    def _failing_handler(event, uow):
        raise RuntimeError("simulated transactional handler failure")

    subscription = dispatcher.subscribe(TenantMembershipActivated, _failing_handler)
    recorder = _Recorder(services)
    try:
        with pytest.raises(RuntimeError, match="simulated transactional handler failure"):
            membership_service.accept_invitation(issued.token)
    finally:
        subscription.dispose()

    assert recorder.events == []
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )
    from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
        SqlAlchemyRoleBindingRepository,
    )

    stored = SqlAlchemyUserTenantMembershipRepository(services["session"]).get(target.id, tenant_id)
    assert stored is not None
    assert stored.status != MEMBERSHIP_STATUS_ACTIVE
    assert SqlAlchemyRoleBindingRepository(services["session"]).list_active_for_principal(
        target.id, tenant_id=tenant_id
    ) == []


def test_post_commit_handler_failure_does_not_block_a_sibling_handler_or_the_commit(services):
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d2-postcommit-isolate"))
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    _set_user_principal(services, target.username)

    bus = membership_service._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    seen = []
    sub_failing = bus.subscribe(TenantMembershipActivated, _failing_handler)
    sub_ok = bus.subscribe(TenantMembershipActivated, lambda e, c: seen.append(e))
    try:
        accepted = membership_service.accept_invitation(issued.token)  # must not raise
    finally:
        sub_failing.dispose()
        sub_ok.dispose()

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert len(seen) == 1
    assert seen[0].membership_id == accepted.id


# ---------------------------------------------------------------------------
# Tenant scope only / cross-tenant isolation
# ---------------------------------------------------------------------------


def test_membership_event_carries_tenant_scope_only_no_organization_id(services):
    tenant_id = _tenant_id(services)
    tenant_context = services["tenant_context_service"]
    other_org = services["organization_service"].create_organization(
        organization_code=_unique_code("P5D2-ORG"), display_name="P5D-2 Org"
    )

    recorder = _Recorder(services)
    target, accepted = _issue_and_accept(services, username=_unique_code("p5d2-tenant-scope"))
    activated = recorder.of(TenantMembershipActivated)[0]
    assert activated.tenant_id == tenant_id
    assert not hasattr(activated, "organization_id")

    # Switch the ambient active organization -- confirmed unrelated to `TenantMembershipService`
    # (P5D-1: `_require_tenant_administrator` resolves `tenant_id` only, never touches
    # organization context) -- the membership event's `tenant_id` must be unaffected.
    tenant_context.set_active_organization(other_org.id)
    removed_recorder = _Recorder(services)
    membership_service = services["tenant_membership_service"]
    removed = membership_service.remove_member(target.id)
    removed_event = removed_recorder.of(TenantMembershipRemoved)[0]
    assert removed_event.tenant_id == tenant_id
    assert removed.id == accepted.id


def test_cross_tenant_actor_cannot_mutate_another_tenants_membership(services):
    from src.tests.ui_runtime_helpers import login_as

    membership_service = services["tenant_membership_service"]
    tenant_context = services["tenant_context_service"]
    auth = services["auth_service"]
    admin_principal = services["user_session"].principal
    home_tenant_id = _tenant_id(services)

    admin_svc = services["tenant_admin_service"]
    other_tenant = admin_svc.create_tenant(_unique_code("P5D2-OTHER"), "P5D-2 Other Tenant")
    services["session"].flush()
    other_username = _unique_code("p5d2-other-tenant-actor")
    auth.register_user(
        other_username,
        _PASSWORD,
        role_names=["tenant_admin"],
        tenant_id=other_tenant.id,
    )
    # a target that only ever exists in the HOME tenant -- not a member of `other_tenant` at all.
    target, _accepted = _issue_and_accept(services, username=_unique_code("p5d2-cross-target"))

    login_as(services, other_username, _PASSWORD)
    tenant_context.set_active_tenant(other_tenant.id)
    recorder = _Recorder(services)
    try:
        with pytest.raises(NotFoundError) as exc:
            # the target's membership lives in the HOME tenant; the other-tenant actor's own
            # active-tenant context resolves to `other_tenant.id`, where no such membership row
            # exists at all.
            membership_service.suspend_member(target.id)
        assert exc.value.code == "TENANT_MEMBERSHIP_NOT_FOUND"
    finally:
        services["user_session"].set_principal(admin_principal)
        tenant_context.set_active_tenant(home_tenant_id)

    assert recorder.events == []
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )

    stored = SqlAlchemyUserTenantMembershipRepository(services["session"]).get(
        target.id, home_tenant_id
    )
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_ACTIVE  # unchanged


# ---------------------------------------------------------------------------
# DomainEventContext separation
# ---------------------------------------------------------------------------


def test_domain_event_context_is_passed_separately_and_never_duplicated_onto_the_event(services):
    recorder = _Recorder(services)
    _target, accepted = _issue_and_accept(services, username=_unique_code("p5d2-context"))

    activated_index = recorder.types().index(TenantMembershipActivated)
    context = recorder.contexts[activated_index]
    assert isinstance(context, DomainEventContext)
    assert context.correlation_id
    event_field_names = {f.name for f in fields(recorder.of(TenantMembershipActivated)[0])}
    assert event_field_names.isdisjoint({"correlation_id", "causation_id", "command_id"})


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def _events_module_source() -> str:
    module = __import__(
        "src.core.platform.domain.tenant.tenancy.events",
        fromlist=["events"],
    )
    return inspect.getsource(module)


def test_membership_events_module_has_no_forbidden_imports():
    source = _events_module_source()
    for forbidden in (
        "sqlalchemy",
        "SQLAlchemy",
        "PySide6",
        "ViewInvalidation",
        "ui_qml",
        "controllers",
        "domain_events",
    ):
        assert forbidden not in source


def test_membership_events_are_frozen_slotted_kw_only_with_exactly_the_approved_fields():
    approved = {"membership_id", "tenant_id", "user_id", "occurred_at"}
    for event_type in _MEMBERSHIP_EVENT_TYPES:
        assert is_dataclass(event_type)
        field_names = {f.name for f in fields(event_type)}
        assert field_names == approved
        instance = event_type(
            membership_id="m", tenant_id="t", user_id="u", occurred_at=datetime.now(timezone.utc)
        )
        with pytest.raises(Exception):
            instance.membership_id = "changed"  # frozen
        with pytest.raises(AttributeError):
            instance.__dict__  # slots -- no instance __dict__ exists


def test_membership_events_never_carry_forbidden_fields():
    forbidden = {
        "actor_id",
        "organization_id",
        "role_id",
        "role_ids",
        "permissions",
        "audit_action",
        "correlation_id",
        "causation_id",
        "command_id",
        "schema_version",
    }
    for event_type in _MEMBERSHIP_EVENT_TYPES:
        field_names = {f.name for f in fields(event_type)}
        assert field_names.isdisjoint(forbidden)


def test_no_disapproved_membership_event_names_exist_anywhere_in_the_events_module():
    source = _events_module_source()
    for forbidden in (
        "TenantMembershipChanged",
        "TenantMembershipStatusChanged",
        "TenantMembershipUpdated",
        "TenantAccessChanged",
        "TenantInvitationRevoked",
    ):
        assert forbidden not in source


def test_issue_invitation_source_never_records_activated():
    """`issue_invitation` covers both the fresh-invite AND reinvite (`removed -> invited`)
    branches -- neither may ever record `TenantMembershipActivated` (section 24/25)."""
    from src.core.platform.application.tenant.tenancy.tenant_membership_service import (
        TenantMembershipService,
    )

    source = inspect.getsource(TenantMembershipService.issue_invitation)
    assert "record_event" not in source
    assert "TenantMembershipActivated" not in source


def test_revoke_invitation_source_never_records_a_membership_event():
    from src.core.platform.application.tenant.tenancy.tenant_membership_service import (
        TenantMembershipService,
    )

    source = inspect.getsource(TenantMembershipService.revoke_invitation)
    assert "uow.record_event(" not in source
