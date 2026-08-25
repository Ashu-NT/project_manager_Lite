
from __future__ import annotations

import inspect
import re
from datetime import datetime, timedelta, timezone

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyRoleBindingRepository,
)
from src.core.platform.infrastructure.persistence.tenant_membership_unit_of_work import (
    SqlAlchemyTenantMembershipUnitOfWork,
)
from src.core.platform.domain.tenant.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_REMOVED,
)

_PASSWORD = "StrongPass123!"
_COUNTER = {"n": 0}


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
# Fresh session per mutation
# ---------------------------------------------------------------------------


def test_fresh_session_per_membership_command(services, monkeypatch):
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d1-fresh-session"))
    seen_sessions = []
    original_create = type(membership_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(membership_service._uow_factory), "create", _spy_create)

    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    membership_service.revoke_invitation(target.id)

    assert len(seen_sessions) == 2
    assert seen_sessions[0] is not seen_sessions[1]
    assert all(s is not services["session"] for s in seen_sessions)


def test_repositories_and_audit_share_the_uow_session(services, monkeypatch):
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d1-shared-session"))
    seen = {}
    original_create = type(membership_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["role_bindings_session"] = uow.role_bindings.session
        seen["auth_sessions_session"] = uow.auth_sessions.session
        seen["audit_session"] = uow.audit.session
        return uow

    monkeypatch.setattr(type(membership_service._uow_factory), "create", _spy_create)

    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    assert seen["uow_session"] is seen["role_bindings_session"]
    assert seen["uow_session"] is seen["auth_sessions_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_no_global_mutation_session_touch(services):
    membership_service = services["tenant_membership_service"]
    target = _register_user(services, _unique_code("p5d1-no-global-touch"))
    legacy_session = services["session"]
    legacy_session.commit()

    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    assert len(legacy_session.new) == 0
    assert len(legacy_session.dirty) == 0


# ---------------------------------------------------------------------------
# Acceptance transaction atomicity: membership + default RoleBinding + audit
# ---------------------------------------------------------------------------


def test_acceptance_emits_exactly_one_role_binding_assigned(services):
    membership_service = services["tenant_membership_service"]
    bus = membership_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingAssigned, lambda e, c: seen.append(e))

    target, accepted = _issue_and_accept(services, username=_unique_code("p5d1-accept-event"))

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert len(seen) == 1
    assert seen[0].principal_id == target.id


def test_acceptance_audit_failure_rolls_back_membership_and_binding_with_zero_observable_event(
    services, monkeypatch
):
    membership_service = services["tenant_membership_service"]
    bus = membership_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingAssigned, lambda e, c: seen.append(e))

    target = _register_user(services, _unique_code("p5d1-accept-audit-fail"))
    tenant_id = _tenant_id(services)
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    _set_user_principal(services, target.username)

    def _fail_audit(self, entry, tenant_id):
        raise RuntimeError("simulated acceptance audit failure")

    monkeypatch.setattr(SqlAlchemyAuditRepository, "add_for_tenant", _fail_audit)

    with pytest.raises(RuntimeError, match="simulated acceptance audit failure"):
        membership_service.accept_invitation(issued.token)

    assert seen == []
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )

    stored = SqlAlchemyUserTenantMembershipRepository(services["session"]).get(target.id, tenant_id)
    assert stored is not None
    assert stored.status != MEMBERSHIP_STATUS_ACTIVE
    assert SqlAlchemyRoleBindingRepository(services["session"]).list_active_for_principal(
        target.id, tenant_id=tenant_id
    ) == []


def test_acceptance_commit_failure_leaves_zero_observable_event(services, monkeypatch):
    membership_service = services["tenant_membership_service"]
    bus = membership_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingAssigned, lambda e, c: seen.append(e))

    target = _register_user(services, _unique_code("p5d1-accept-commit-fail"))
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    _set_user_principal(services, target.username)

    def _fail_commit(self):
        raise RuntimeError("simulated acceptance commit failure")

    monkeypatch.setattr(SqlAlchemyTenantMembershipUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated acceptance commit failure"):
        membership_service.accept_invitation(issued.token)

    assert seen == []


# ---------------------------------------------------------------------------
# Removal transaction atomicity: membership + binding revocations + AuthSession + audit
# ---------------------------------------------------------------------------


def test_removal_emits_one_role_binding_revoked_per_genuinely_active_binding(services):
    membership_service = services["tenant_membership_service"]
    bus = membership_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingRevoked, lambda e, c: seen.append(e))

    target, _accepted = _issue_and_accept(services, username=_unique_code("p5d1-remove-event"))
    removed = membership_service.remove_member(target.id)

    assert removed.status == MEMBERSHIP_STATUS_REMOVED
    assert len(seen) == 1  # exactly the single default `viewer` binding granted on acceptance
    assert seen[0].principal_id == target.id


def test_removal_audit_failure_rolls_back_membership_and_bindings_with_zero_observable_event(
    services, monkeypatch
):
    membership_service = services["tenant_membership_service"]
    bus = membership_service._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(RoleBindingRevoked, lambda e, c: seen.append(e))

    target, _accepted = _issue_and_accept(
        services, username=_unique_code("p5d1-remove-audit-fail")
    )
    tenant_id = _tenant_id(services)

    def _fail_audit(self, entry, tenant_id):
        raise RuntimeError("simulated removal audit failure")

    monkeypatch.setattr(SqlAlchemyAuditRepository, "add_for_tenant", _fail_audit)

    with pytest.raises(RuntimeError, match="simulated removal audit failure"):
        membership_service.remove_member(target.id)

    assert seen == []
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )

    stored = SqlAlchemyUserTenantMembershipRepository(services["session"]).get(target.id, tenant_id)
    assert stored is not None
    assert stored.status != MEMBERSHIP_STATUS_REMOVED
    assert SqlAlchemyRoleBindingRepository(services["session"]).list_active_for_principal(
        target.id, tenant_id=tenant_id
    ) != []  # the default binding must still be active -- nothing was actually revoked


# ---------------------------------------------------------------------------
# suspend_member / reactivate_member: verified (not assumed) to never touch RoleBinding
# ---------------------------------------------------------------------------


def test_suspend_and_reactivate_never_emit_a_role_binding_event(services):
    membership_service = services["tenant_membership_service"]
    bus = membership_service._uow_factory._post_commit_bus
    seen_assigned = []
    seen_revoked = []
    bus.subscribe(RoleBindingAssigned, lambda e, c: seen_assigned.append(e))
    bus.subscribe(RoleBindingRevoked, lambda e, c: seen_revoked.append(e))

    target, _accepted = _issue_and_accept(services, username=_unique_code("p5d1-suspend-no-rb"))
    seen_assigned.clear()  # drop the acceptance's own default-grant event; not under test here
    tenant_id = _tenant_id(services)

    suspended = membership_service.suspend_member(target.id)
    reactivated = membership_service.reactivate_member(target.id)

    assert suspended.status != MEMBERSHIP_STATUS_ACTIVE
    assert reactivated.status == MEMBERSHIP_STATUS_ACTIVE
    assert seen_assigned == []
    assert seen_revoked == []
    assert SqlAlchemyRoleBindingRepository(services["session"]).list_active_for_principal(
        target.id, tenant_id=tenant_id
    ) != []  # the default binding survives suspend+reactivate untouched


# ---------------------------------------------------------------------------
# Last-admin guard atomicity
# ---------------------------------------------------------------------------


def test_last_admin_suspend_and_remove_fail_atomically_with_zero_side_effects(services):
    membership_service = services["tenant_membership_service"]
    tenant_id = _tenant_id(services)
    auth = services["auth_service"]
    target = auth.register_user(
        _unique_code("p5d1-last-admin"),
        _PASSWORD,
        role_names=("tenant_admin",),
        tenant_id=tenant_id,
    )
    bus = membership_service._uow_factory._post_commit_bus
    seen_revoked = []
    bus.subscribe(RoleBindingRevoked, lambda e, c: seen_revoked.append(e))

    with pytest.raises(BusinessRuleError) as suspend_error:
        membership_service.suspend_member(target.id)
    assert suspend_error.value.code == "TENANT_LAST_ADMIN_REQUIRED"

    with pytest.raises(BusinessRuleError) as remove_error:
        membership_service.remove_member(target.id)
    assert remove_error.value.code == "TENANT_LAST_ADMIN_REQUIRED"

    assert seen_revoked == []
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )

    stored = SqlAlchemyUserTenantMembershipRepository(services["session"]).get(target.id, tenant_id)
    assert stored is not None
    assert stored.status == MEMBERSHIP_STATUS_ACTIVE


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def _strip_docstrings_and_comments(source: str) -> str:
    """Architecture guards below check for real code patterns (a call, an attribute touch), not
    prose -- this module's own docstrings legitimately narrate the pre-P5D-1 bypasses being
    removed and the sibling capability being mirrored, which would otherwise false-positive a
    naive raw-source `in` check."""
    without_triple_quoted = re.sub(r'"""[\s\S]*?"""', "", source)
    return re.sub(r"#.*", "", without_triple_quoted)


def _tenant_membership_service_source(*, code_only: bool = False) -> str:
    module = __import__(
        "src.core.platform.application.tenant.tenancy.tenant_membership_service",
        fromlist=["tenant_membership_service"],
    )
    source = inspect.getsource(module)
    return _strip_docstrings_and_comments(source) if code_only else source


def _role_binding_mutation_participant_source(*, code_only: bool = False) -> str:
    module = __import__(
        "src.core.platform.application.security.authorization.roles.role_binding_mutation_participant",
        fromlist=["role_binding_mutation_participant"],
    )
    source = inspect.getsource(module)
    return _strip_docstrings_and_comments(source) if code_only else source


def test_tenant_membership_service_has_no_inline_commit_or_rollback_or_global_session():
    source = _tenant_membership_service_source()
    for forbidden in (
        "self._session.commit(",
        "self._session.rollback(",
        "self._session =",
        "self._session:",
    ):
        assert forbidden not in source


def test_tenant_membership_service_has_no_direct_role_binding_repository_bypass():
    """The two P5D-SEM-discovered bypasses (`_ensure_default_role_bindings`'s direct `add()`,
    `remove_member`'s raw bulk `revoke_active_for_principal_tenant`) must be gone -- replaced
    by the shared, canonical `role_binding_mutation_participant` mechanics."""
    source = _tenant_membership_service_source(code_only=True)
    assert "role_bindings.add(" not in source
    assert "revoke_active_for_principal_tenant" not in source
    assert "RoleBinding.create(" not in source
    assert "create_role_binding_using(" in source
    assert "revoke_role_binding_using(" in source


def test_tenant_membership_service_never_calls_role_governance_service():
    """The RoleBinding mechanics are reused via the transaction-agnostic participant module,
    never through a nested `RoleGovernanceService` public-command call (which would open a
    second, independent transaction)."""
    source = _tenant_membership_service_source(code_only=True)
    assert "RoleGovernanceService" not in source
    assert "role_governance_service" not in source


def test_tenant_membership_service_adds_no_p5d3_ui_vocabulary():
    """P5D-1/P5D-2 are transaction convergence and typed DomainEvents only -- ViewInvalidation
    and any Qt/UI wiring for membership are P5D-3's job, not started here. (The four
    `TenantMembership*` event names are legitimately P5D-2 vocabulary as of this phase --
    see `test_tenant_membership_typed_events.py` for their own positive/negative coverage.)"""
    source = _tenant_membership_service_source()
    for forbidden in ("ViewInvalidation", "PySide6", "ui_qml"):
        assert forbidden not in source


def test_role_binding_mutation_participant_owns_no_transaction():
    """The shared participant module must remain transaction-agnostic: no `commit()`,
    `rollback()`, UoW construction, or Session construction of its own -- both
    `RoleGovernanceService` and `TenantMembershipService` supply their own session-bound
    repos/audit/clock/record_event and own the surrounding transaction themselves."""
    source = _role_binding_mutation_participant_source(code_only=True)
    for forbidden in (
        ".commit(",
        ".rollback(",
        "UnitOfWork(",
        "sessionmaker(",
        "Session(",
    ):
        assert forbidden not in source
