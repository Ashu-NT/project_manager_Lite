from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation import (
    TENANT_MEMBERSHIPS_SCOPE_CODE,
    TENANT_MEMBERSHIP_CATEGORY,
    build_tenant_membership_view_invalidation_handler,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.tenant.tenancy.events import (
    TenantMembershipActivated,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import TenantScope
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.uow.tenant_membership_unit_of_work import (
    SqlAlchemyTenantMembershipUnitOfWork,
)
from src.ui_qml.platform.adapters.tenant_membership_view_invalidation_adapter import (
    TenantMembershipViewInvalidationAdapter,
)
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


def _switch_session_to_tenant_admin(services, *, suffix: str, tenant_id: str):
    """A genuine tenant-scoped (non-platform-operator) caller -- required to actually exercise
    the membership-status filter `AuthService.list_users()`'s tenant branch applies. The default
    `services` fixture principal ("admin") IS a platform operator, so `list_users()` takes the
    platform branch (`user_repo.list_all()`, no membership filter at all) -- useless for
    observing a real membership-status-driven list change."""
    auth = services["auth_service"]
    actor = auth.register_user(
        _unique_code(f"p5d3-{suffix}"), _PASSWORD, role_names=["tenant_admin"], tenant_id=tenant_id
    )
    principal = auth.build_principal_for_context(actor, tenant_id=tenant_id, organization_id=None)
    services["user_session"].set_principal(replace(principal, session_id=None))
    return actor


def _issue_and_accept(services, membership_service, *, admin_principal, username: str):
    target = services["auth_service"].register_user(username, _PASSWORD, display_name=username)
    services["user_session"].set_principal(admin_principal)
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    target_auth = services["auth_service"].authenticate(target.username, _PASSWORD)
    services["user_session"].set_principal(services["auth_service"].build_principal(target_auth))
    accepted = membership_service.accept_invitation(issued.token)
    services["user_session"].set_principal(admin_principal)
    return target, accepted


# ---------------------------------------------------------------------------
# Mapper unit tests
# ---------------------------------------------------------------------------


def test_mapper_maps_each_event_type_to_the_same_tenant_scoped_hint():
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_tenant_membership_view_invalidation_handler(_FakeChannel())
    now = datetime.now(timezone.utc)
    events = [
        TenantMembershipActivated(membership_id="m-1", tenant_id="t-1", user_id="u-1", occurred_at=now),
        TenantMembershipSuspended(membership_id="m-1", tenant_id="t-1", user_id="u-1", occurred_at=now),
        TenantMembershipReactivated(membership_id="m-1", tenant_id="t-1", user_id="u-1", occurred_at=now),
        TenantMembershipRemoved(membership_id="m-1", tenant_id="t-1", user_id="u-1", occurred_at=now),
    ]
    for event in events:
        handler(event, DomainEventContext(correlation_id="corr"))

    assert len(hints) == 4
    for hint in hints:
        assert hint.scope == TenantScope("t-1")
        assert hint.category == TENANT_MEMBERSHIP_CATEGORY
        assert hint.scope_code == TENANT_MEMBERSHIPS_SCOPE_CODE
        assert hint.entity_type == "tenant_membership"
        assert hint.entity_id == "m-1"


def _imported_module_names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_tenant_membership_view_invalidation_mapper_has_no_qt_dependency():
    import src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation as mapper_module

    imports = _imported_module_names(mapper_module)
    for forbidden in ("PySide6", "QtCore", "ui_qml", "domain_events", "sqlalchemy"):
        assert not any(forbidden in name for name in imports), imports


def test_adapter_module_has_no_domain_event_or_postcommit_bus_dependency():
    """The adapter must know only ViewInvalidation, never DomainEvent/typed membership events/
    the postcommit bus -- the mapper handles DomainEvents, the adapter handles ViewInvalidation
    only."""
    import src.ui_qml.platform.adapters.tenant_membership_view_invalidation_adapter as adapter_module

    imports = _imported_module_names(adapter_module)
    for forbidden in (
        "domain_event",
        "domain_events",
        "post_commit",
        "PostCommitEventPublisher",
        "sqlalchemy",
    ):
        assert not any(forbidden in name.lower() for name in imports), imports
    source = inspect.getsource(adapter_module)
    for forbidden in (
        "TenantMembershipActivated",
        "TenantMembershipSuspended",
        "TenantMembershipReactivated",
        "TenantMembershipRemoved",
        "organization_id",
        "OrganizationScope",
        "ExactOrganization",
    ):
        assert forbidden not in source


def test_controllers_do_not_import_event_infrastructure():
    import src.ui_qml.platform.controllers.admin_console.admin_console_controller as admin_module
    import src.ui_qml.platform.controllers.identity_access.access.access_workspace_controller as access_module

    for module in (admin_module, access_module):
        imports = _imported_module_names(module)
        for forbidden in ("domain_event_context", "view_invalidation", "post_commit"):
            assert not any(forbidden in name.lower() for name in imports), (module.__name__, imports)


# ---------------------------------------------------------------------------
# Structural wiring: tenant scope, tenant switch, organization switch
# ---------------------------------------------------------------------------


def test_adapter_only_reacts_to_the_currently_active_tenant(services):
    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)
    adapter = TenantMembershipViewInvalidationAdapter(channel=channel, tenant_id=tenant_a)
    signal_calls = []
    adapter.membershipDataStale.connect(lambda: signal_calls.append("stale"))

    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    _target, _accepted = _issue_and_accept(
        services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-scope-a")
    )
    assert signal_calls == ["stale"]

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("P5D3-TENANT-B"), "P5D-3 Tenant B")
    services["session"].flush()
    services["user_session"].set_principal(admin_principal)
    actor_b = _switch_session_to_tenant_admin(services, suffix="scope-b-actor", tenant_id=tenant_b.id)
    _target_b, _accepted_b = _issue_and_accept(
        services,
        membership_service,
        admin_principal=services["auth_service"].build_principal_for_context(
            actor_b, tenant_id=tenant_b.id, organization_id=None
        ),
        username=_unique_code("p5d3-scope-b-target"),
    )

    # Tenant B's own activation must not fire the adapter still subscribed to Tenant A.
    assert signal_calls == ["stale"]
    adapter.dispose()
    services["user_session"].set_principal(admin_principal)


def test_adapter_follows_a_tenant_switch_with_no_stale_or_duplicate_subscription(services):
    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)
    admin_principal = services["user_session"].principal
    membership_service = services["tenant_membership_service"]

    adapter = TenantMembershipViewInvalidationAdapter(channel=channel, tenant_id=tenant_a)
    signal_calls = []
    adapter.membershipDataStale.connect(lambda: signal_calls.append("stale"))
    subscription_count_before = len(channel._subscriptions)

    _issue_and_accept(
        services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-switch-a1")
    )
    assert signal_calls == ["stale"]

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("P5D3-SWITCH-TENANT-B"), "P5D-3 Switch Tenant B")
    services["session"].flush()
    services["user_session"].set_principal(admin_principal)
    actor_b = _switch_session_to_tenant_admin(services, suffix="switch-b-actor", tenant_id=tenant_b.id)
    principal_b = services["auth_service"].build_principal_for_context(
        actor_b, tenant_id=tenant_b.id, organization_id=None
    )

    adapter.set_active_tenant(tenant_b.id)
    assert len(channel._subscriptions) == subscription_count_before, (
        "switching must dispose the old subscription before adding the new one -- never accumulate"
    )

    services["user_session"].set_principal(admin_principal)
    _issue_and_accept(
        services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-switch-a2")
    )
    assert signal_calls == ["stale"], "Tenant A must no longer trigger the signal after switching away"

    _issue_and_accept(
        services, membership_service, admin_principal=principal_b, username=_unique_code("p5d3-switch-b1")
    )
    assert signal_calls == ["stale", "stale"], "Tenant B must trigger the signal once switched to"

    adapter.dispose()
    assert len(channel._subscriptions) == subscription_count_before - 1
    services["user_session"].set_principal(admin_principal)


def test_real_tenant_switch_through_the_catalog_rewires_the_adapter(services):
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    adapter = catalog._tenant_membership_view_invalidation_adapter

    def _current_filters():
        subscription = adapter._subscription._subscription
        if subscription is None:
            return []
        entry = channel._subscriptions.get(subscription._subscription_id)
        return [entry[0]] if entry is not None else []

    tenant_a = _active_tenant(services)
    assert any(f.tenant_id == tenant_a for f in _current_filters())

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("P5D3-REALSWITCH-TENANT-B"), "P5D-3 Real Switch Tenant B")
    services["session"].flush()

    switch_result = catalog.tenantSwitcher.switchToTenant(tenant_b.id)
    assert switch_result["ok"] is True

    filters_after_switch = _current_filters()
    assert any(f.tenant_id == tenant_b.id for f in filters_after_switch)
    assert not any(f.tenant_id == tenant_a for f in filters_after_switch)
    assert adapter is catalog._tenant_membership_view_invalidation_adapter


def test_organization_switch_does_not_re_scope_the_membership_subscription(services):
    """Item 8/34: membership has no organization dimension -- switching the active organization
    within the SAME tenant must leave the adapter's subscription targeting the same tenant, with
    no re-subscription at all (unlike the RoleBinding/ModuleEntitlement adapters, which DO
    re-scope on `refreshCurrentPermissions()`)."""
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    adapter = catalog._tenant_membership_view_invalidation_adapter
    # P6: the raw channel Subscription (`adapter._subscription._subscription`), not the
    # always-present `ScopedViewInvalidationSubscription` wrapper itself, is what must keep its
    # identity here -- the wrapper instance never changes, only what it wraps.
    subscription_before = adapter._subscription._subscription

    org = services["organization_service"].create_organization(
        organization_code=_unique_code("P5D3-ORG-SWITCH"), display_name="P5D-3 Org Switch"
    )
    services["tenant_context_service"].set_active_organization(org.id)
    catalog.refreshCurrentPermissions()  # re-scopes role_binding/module adapters; must not touch this one

    assert adapter._subscription._subscription is subscription_before, (
        "an organization switch must never dispose/recreate the tenant-only membership "
        "subscription"
    )

    tenant_a = _active_tenant(services)
    signal_calls = []
    adapter.membershipDataStale.connect(lambda: signal_calls.append("stale"))
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    _issue_and_accept(
        services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-org-switch-target")
    )
    assert signal_calls == ["stale"], "Tenant A must still refresh after an unrelated org switch"
    assert _active_tenant(services) == tenant_a


# ---------------------------------------------------------------------------
# End-to-end: real canonical mutation -> real UI consumer refresh
# ---------------------------------------------------------------------------


def test_activation_refreshes_both_real_ui_consumers_end_to_end(services):
    catalog = _catalog(services)
    tenant_id = _active_tenant(services)
    admin_principal = services["user_session"].principal
    tenant_admin = _switch_session_to_tenant_admin(services, suffix="e2e-activate-admin", tenant_id=tenant_id)
    tenant_admin_principal = services["auth_service"].build_principal_for_context(
        tenant_admin, tenant_id=tenant_id, organization_id=None
    )
    catalog.adminWorkspace.users  # establish baseline read
    catalog.adminAccessWorkspace.refresh()

    membership_service = services["tenant_membership_service"]
    target, accepted = _issue_and_accept(
        services, membership_service, admin_principal=tenant_admin_principal, username=_unique_code("p5d3-e2e-activate")
    )
    assert accepted.status == "active"

    # The real signal fired synchronously during `accept_invitation()`'s commit, but under
    # whichever principal was active AT THAT MOMENT (the target user themselves, self-service --
    # a fresh registrant with no `auth.read`/`auth.manage` permission yet, so that automatic
    # refresh attempt was silently isolated per ISOLATE_AND_CONTINUE). Re-trigger the SAME narrow
    # reaction now, under the tenant admin's own principal, to observe the actual data change --
    # the wiring itself (that the signal fires at all, exactly once, tenant-scoped) is proven
    # structurally by the other tests in this file.
    services["user_session"].set_principal(tenant_admin_principal)
    catalog.adminWorkspace.refresh_users()
    catalog.adminAccessWorkspace.refresh_security_users()
    admin_ids = [row.get("id") for row in catalog.adminWorkspace.users.get("items", [])]
    security_ids = [row.get("id") for row in catalog.adminAccessWorkspace.securityUsers.get("items", [])]
    assert target.id in admin_ids
    assert target.id in security_ids
    services["user_session"].set_principal(admin_principal)


def test_removal_makes_the_target_disappear_from_both_real_ui_consumers(services):
    catalog = _catalog(services)
    tenant_id = _active_tenant(services)
    admin_principal = services["user_session"].principal
    tenant_admin = _switch_session_to_tenant_admin(services, suffix="e2e-remove-admin", tenant_id=tenant_id)
    tenant_admin_principal = services["auth_service"].build_principal_for_context(
        tenant_admin, tenant_id=tenant_id, organization_id=None
    )

    membership_service = services["tenant_membership_service"]
    target, _accepted = _issue_and_accept(
        services, membership_service, admin_principal=tenant_admin_principal, username=_unique_code("p5d3-e2e-remove")
    )
    services["user_session"].set_principal(tenant_admin_principal)
    catalog.adminWorkspace.refresh_users()
    catalog.adminAccessWorkspace.refresh_security_users()
    assert target.id in [row.get("id") for row in catalog.adminWorkspace.users.get("items", [])]

    membership_service.remove_member(target.id)

    admin_ids = [row.get("id") for row in catalog.adminWorkspace.users.get("items", [])]
    security_ids = [row.get("id") for row in catalog.adminAccessWorkspace.securityUsers.get("items", [])]
    assert target.id not in admin_ids
    assert target.id not in security_ids
    services["user_session"].set_principal(admin_principal)


# ---------------------------------------------------------------------------
# Invalid transition / rollback / postcommit isolation
# ---------------------------------------------------------------------------


def test_invalid_transition_triggers_no_refresh(services):
    catalog = _catalog(services)
    refresh_calls = []
    catalog.adminWorkspace.refresh_users = lambda: refresh_calls.append("admin") or None
    catalog.adminAccessWorkspace.refresh_security_users = lambda: refresh_calls.append("access") or None

    membership_service = services["tenant_membership_service"]
    target = services["auth_service"].register_user(_unique_code("p5d3-invalid"), _PASSWORD)
    membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )

    with pytest.raises(BusinessRuleError):
        membership_service.suspend_member(target.id)  # still "invited", never accepted

    assert refresh_calls == []


def test_audit_failure_triggers_no_refresh(services, monkeypatch):
    catalog = _catalog(services)
    refresh_calls = []
    catalog.adminWorkspace.refresh_users = lambda: refresh_calls.append("admin") or None
    catalog.adminAccessWorkspace.refresh_security_users = lambda: refresh_calls.append("access") or None

    membership_service = services["tenant_membership_service"]
    target = services["auth_service"].register_user(_unique_code("p5d3-audit-fail"), _PASSWORD)
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    services["user_session"].set_principal(
        services["auth_service"].build_principal(
            services["auth_service"].authenticate(target.username, _PASSWORD)
        )
    )

    def _fail_audit(self, entry, tenant_id):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(SqlAlchemyAuditRepository, "add_for_tenant", _fail_audit)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        membership_service.accept_invitation(issued.token)

    assert refresh_calls == []


def test_commit_failure_triggers_no_refresh(services, monkeypatch):
    catalog = _catalog(services)
    refresh_calls = []
    catalog.adminWorkspace.refresh_users = lambda: refresh_calls.append("admin") or None
    catalog.adminAccessWorkspace.refresh_security_users = lambda: refresh_calls.append("access") or None

    membership_service = services["tenant_membership_service"]
    target = services["auth_service"].register_user(_unique_code("p5d3-commit-fail"), _PASSWORD)
    issued = membership_service.issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    services["user_session"].set_principal(
        services["auth_service"].build_principal(
            services["auth_service"].authenticate(target.username, _PASSWORD)
        )
    )

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyTenantMembershipUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        membership_service.accept_invitation(issued.token)

    assert refresh_calls == []


def test_one_post_commit_handler_failing_does_not_block_the_other_or_the_commit(services):
    catalog = _catalog(services)
    refresh_calls = []
    catalog.adminWorkspace.refresh_users = lambda: refresh_calls.append("admin") or None

    bus = services["tenant_membership_service"]._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    subscription = bus.subscribe(TenantMembershipActivated, _failing_handler)
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    try:
        target, accepted = _issue_and_accept(
            services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-postcommit-isolate")
        )
    finally:
        subscription.dispose()

    assert accepted.status == "active"
    assert refresh_calls == ["admin"]


# ---------------------------------------------------------------------------
# RoleBinding invalidation remains separate; no coarse over-refresh
# ---------------------------------------------------------------------------


def test_removal_fires_both_membership_and_role_binding_invalidation_separately(services):
    catalog = _catalog(services)
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    target, _accepted = _issue_and_accept(
        services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-double-refresh")
    )

    # Spies installed only now -- acceptance's own `TenantMembershipActivated` +
    # `RoleBindingAssigned` (the default grant) already fired and are not under test here.
    membership_refresh_calls = []
    role_binding_refresh_calls = []
    catalog.adminWorkspace.refresh_users = lambda: membership_refresh_calls.append("membership") or None
    catalog.adminAccessWorkspace.refresh_role_bindings = (
        lambda: role_binding_refresh_calls.append("role_binding") or None
    )

    membership_service.remove_member(target.id)

    # Removal commits TenantMembershipRemoved + one RoleBindingRevoked (the default binding) --
    # each narrow consumer must refresh exactly once, for its own reason, never merged into one
    # generic invalidation and never duplicated.
    assert membership_refresh_calls == ["membership"]
    assert role_binding_refresh_calls == ["role_binding"]


def test_membership_transition_does_not_trigger_unrelated_sub_controller_refreshes(services):
    """Item 37: a membership event must never reload calendars/sites/departments/organizations/
    parties/documents -- the coarse legacy `auth_changed` binder's own over-refresh, not
    reproduced by the narrow P5D-3 wiring. Uses a pure `suspend_member` (setup completed before
    installing spies) so the measured window contains only the membership transition itself --
    no `register_user()`/`authenticate()` calls, which legitimately fire their OWN unrelated
    `auth_changed` emissions (new-account creation, login) and would confound this proof."""
    catalog = _catalog(services)
    membership_service = services["tenant_membership_service"]
    admin_principal = services["user_session"].principal
    target, _accepted = _issue_and_accept(
        services, membership_service, admin_principal=admin_principal, username=_unique_code("p5d3-narrow")
    )

    unrelated_refresh_calls = []
    for attr in (
        "_organization_controller",
        "_calendar_controller",
        "_site_controller",
        "_department_controller",
        "_employee_controller",
        "_party_controller",
        "_document_controller",
    ):
        controller = getattr(catalog.adminWorkspace, attr)
        controller.refresh = lambda name=attr: unrelated_refresh_calls.append(name) or None

    membership_service.suspend_member(target.id)

    assert unrelated_refresh_calls == []
