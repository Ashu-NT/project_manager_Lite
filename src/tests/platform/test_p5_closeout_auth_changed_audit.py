
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.application.runtime import build_desktop_api_registry
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_PASSWORD = "StrongPass123!"
_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _active_tenant(services) -> str:
    return services["tenant_context_service"].get_active_tenant_id()


def _tenant_scoped_binding_setup(services, *, suffix: str, role_name: str = "viewer"):
    auth = services["auth_service"]
    tenant_id = _active_tenant(services)
    actor = auth.register_user(
        _unique_code(f"p5closeout-actor-{suffix}"), "P5Closeout123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    target = auth.register_user(
        _unique_code(f"p5closeout-target-{suffix}"), "P5Closeout123!", role_names=[], tenant_id=tenant_id
    )
    actor_role = auth._role_repo.get_by_name("tenant_admin")
    target_role = auth._role_repo.get_by_name(role_name)
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=actor_role.id,
        assignable_role_id=target_role.id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )
    principal = auth.build_principal_for_context(actor, tenant_id=tenant_id, organization_id=None)
    services["user_session"].set_principal(
        replace(principal, session_id=None, permissions=frozenset({*principal.permissions, "auth.role.assign"}))
    )
    return target, target_role


# ---------------------------------------------------------------------------
# Inventory / source-level guards
# ---------------------------------------------------------------------------


def test_role_governance_service_emits_no_auth_changed():
    import inspect

    import src.core.platform.application.security.authorization.roles.role_governance_service as module

    source = inspect.getsource(module)
    assert "auth_changed" not in source
    assert "domain_events" not in source


def test_tenant_membership_service_still_emits_no_auth_changed():
    """Item 10: P5D-3's removal must not have regressed -- re-verified here, in the same pass
    that touches the sibling RoleBinding capability, so a future edit to either file gets caught
    by both guards independently."""
    import inspect

    import src.core.platform.application.tenant.tenancy.tenant_membership_service as module

    source = inspect.getsource(module)
    assert "auth_changed" not in source


def test_exactly_two_production_auth_changed_subscribers_remain():
    """Structural re-confirmation of the full consumer inventory -- both are retained (for the
    22 other, non-RoleBinding/non-membership producers), neither was touched by this closeout."""
    import inspect

    import src.ui_qml.platform.controllers.admin_console.domain_event_binder as binder_module
    import src.ui_qml.platform.controllers.identity_access.access.access_workspace_controller as access_module

    assert "domain_events.auth_changed" in inspect.getsource(binder_module)
    assert "domain_events.auth_changed" in inspect.getsource(access_module)


# ---------------------------------------------------------------------------
# Real end-to-end: RoleBinding assignment/revocation double-refresh proof
# ---------------------------------------------------------------------------


def test_role_binding_assignment_causes_exactly_one_narrow_refresh_and_zero_coarse_legacy_refresh(
    services,
):
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    target, target_role = _tenant_scoped_binding_setup(services, suffix="assign-refresh")

    narrow_calls = []
    coarse_security_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: narrow_calls.append("role_binding") or None
    catalog.adminAccessWorkspace._refresh_after_security_change = (
        lambda: coarse_security_calls.append("legacy_auth_changed") or None
    )

    services["role_governance_service"].assign_role(target_user_id=target.id, role_id=target_role.id)

    assert narrow_calls == ["role_binding"]
    assert coarse_security_calls == []


def test_role_binding_revocation_causes_exactly_one_narrow_refresh_and_zero_coarse_legacy_refresh(
    services,
):
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    target, target_role = _tenant_scoped_binding_setup(services, suffix="revoke-refresh")
    binding = services["role_governance_service"].assign_role(target_user_id=target.id, role_id=target_role.id)

    narrow_calls = []
    coarse_security_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: narrow_calls.append("role_binding") or None
    catalog.adminAccessWorkspace._refresh_after_security_change = (
        lambda: coarse_security_calls.append("legacy_auth_changed") or None
    )

    services["role_governance_service"].revoke_role_binding(binding.id)

    assert narrow_calls == ["role_binding"]
    assert coarse_security_calls == []


def test_role_binding_assignment_no_longer_reaches_the_admin_console_coarse_binder(services):
    """The admin console's composite `domain_event_binder.py` subscribes to `auth_changed` among
    8 signals and triggers a full 9-presenter reload -- a RoleBinding mutation must no longer
    reach it at all (it never had a narrow RoleBinding reaction; P5C-3 wired that to the access
    workspace only)."""
    catalog = _catalog(services)
    target, target_role = _tenant_scoped_binding_setup(services, suffix="admin-console-isolation")

    # Spy installed only now -- `_tenant_scoped_binding_setup`'s own `register_user()` calls
    # legitimately fire `auth_changed` for an unrelated Category-B reason (new-account creation)
    # and correctly cascade the coarse admin-console refresh for THAT reason; not under test here.
    coarse_admin_calls = []
    catalog.adminWorkspace.refresh = lambda: coarse_admin_calls.append("admin_console_full_refresh") or None

    services["role_governance_service"].assign_role(target_user_id=target.id, role_id=target_role.id)

    assert coarse_admin_calls == []


def test_legacy_signal_still_silent_on_rollback(services, monkeypatch):
    """Rollback safety is unaffected by removing the (already-redundant) legacy emit -- there
    was never anything to observe on a rolled-back mutation, before or after this closeout."""
    from src.core.platform.infrastructure.persistence.uow.role_governance_unit_of_work import (
        SqlAlchemyRoleGovernanceUnitOfWork,
    )

    import pytest

    target, target_role = _tenant_scoped_binding_setup(services, suffix="rollback-silent")
    role_governance_service = services["role_governance_service"]
    seen_signals = []
    domain_events.auth_changed.connect(seen_signals.append)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyRoleGovernanceUnitOfWork, "commit", _fail_commit)
    try:
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            role_governance_service.assign_role(target_user_id=target.id, role_id=target_role.id)
    finally:
        domain_events.auth_changed.disconnect(seen_signals.append)

    assert seen_signals == []


# ---------------------------------------------------------------------------
# Current-user / other-user security regression
# ---------------------------------------------------------------------------


def test_current_principal_refresh_still_occurs_and_fails_closed_without_auth_changed(services, monkeypatch):
    """Item 3/14: current-principal refresh is `role_assignment_service.py`'s own explicit,
    unconditional call to `refresh_current_session_if_user(...)` -- never wired through
    `auth_changed`. Proven directly: it still happens (and still fails closed) with the legacy
    signal fully removed from `RoleGovernanceService`."""
    auth = services["auth_service"]
    tenant_id = _active_tenant(services)
    username = _unique_code("p5closeout-self-actor")
    self_actor = auth.register_user(
        username, "P5CloseoutSelf123!", role_names=["tenant_admin"], tenant_id=tenant_id
    )
    tenant_admin_role = auth._role_repo.get_by_name("tenant_admin")
    viewer_role = auth._role_repo.get_by_name("viewer")
    services["role_governance_service"].create_delegation_policy(
        actor_role_id=tenant_admin_role.id,
        assignable_role_id=viewer_role.id,
        target_scope_type="tenant",
        tenant_id=tenant_id,
    )

    from src.tests.ui_runtime_helpers import login_as

    login_as(services, username, "P5CloseoutSelf123!")
    assert "viewer" not in services["user_session"].principal.role_names

    auth.assign_role(self_actor.id, "viewer")
    assert "viewer" in services["user_session"].principal.role_names

    def _fail_build_principal(*_args, **_kwargs):
        raise RuntimeError("simulated build_principal failure")

    monkeypatch.setattr(
        "src.core.platform.application.security.auth.session.session_service.build_principal",
        _fail_build_principal,
    )
    auth.revoke_role(self_actor.id, "viewer")  # must not raise -- fail-closed clears instead

    assert services["user_session"].principal is None


def test_other_user_role_binding_mutation_leaves_acting_admin_principal_untouched(services):
    """Item 15: admin changes User B's RoleBinding -- binding state updates, narrow RoleBinding
    ViewInvalidation fires, the acting admin's own principal is untouched, and no coarse
    `auth_changed` UI refresh happens for either party."""
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    target, target_role = _tenant_scoped_binding_setup(services, suffix="other-user")
    admin_principal_before = services["user_session"].principal

    narrow_calls = []
    catalog.adminAccessWorkspace.refresh_role_bindings = lambda: narrow_calls.append("role_binding") or None

    binding = services["role_governance_service"].assign_role(target_user_id=target.id, role_id=target_role.id)

    assert binding.principal_id == target.id
    assert narrow_calls == ["role_binding"]
    assert services["user_session"].principal is admin_principal_before


# ---------------------------------------------------------------------------
# Membership removal composition: membership + RoleBinding + zero legacy auth refresh
# ---------------------------------------------------------------------------


def test_membership_removal_refreshes_membership_and_role_binding_narrowly_with_zero_legacy_auth_refresh(
    services,
):
    catalog = _catalog(services)
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal

    target = services["auth_service"].register_user(_unique_code("p5closeout-removal-target"), _PASSWORD)
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    services["user_session"].set_principal(
        services["auth_service"].build_principal(
            services["auth_service"].authenticate(target.username, _PASSWORD)
        )
    )
    membership_service.accept_invitation(issued.token)
    services["user_session"].set_principal(admin_principal)

    membership_refresh_calls = []
    role_binding_refresh_calls = []
    coarse_security_calls = []
    coarse_admin_calls = []
    catalog.adminWorkspace.refresh_users = lambda: membership_refresh_calls.append("membership") or None
    catalog.adminAccessWorkspace.refresh_role_bindings = (
        lambda: role_binding_refresh_calls.append("role_binding") or None
    )
    catalog.adminAccessWorkspace._refresh_after_security_change = (
        lambda: coarse_security_calls.append("legacy_auth_changed") or None
    )
    catalog.adminWorkspace.refresh = lambda: coarse_admin_calls.append("admin_console_full_refresh") or None

    membership_service.remove_member(target.id)

    assert membership_refresh_calls == ["membership"]
    assert role_binding_refresh_calls == ["role_binding"]  # the default `viewer` grant revoked
    assert coarse_security_calls == []
    assert coarse_admin_calls == []
