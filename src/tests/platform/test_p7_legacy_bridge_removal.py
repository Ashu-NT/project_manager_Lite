"""P7: pre-release removal of generic legacy-bridge residue for the five already-modernized
capabilities (Organization, Module Entitlement, RoleBinding, TenantMembership, Approval), plus
proof that the still-unmodernized capabilities' own direct legacy-signal wiring (e.g.
`auth_changed` -> `AccessWorkspaceController._on_auth_changed`) is unaffected and stays narrow.

Explicitly NOT modernizing any further capability, NOT touching `admin_console/domain_event_binder
.py` (proven to already be direct wiring with a real, still-required composite-refresh
responsibility, not generic bridge routing), and NOT touching PM/Inventory's own extensive,
still-genuinely-needed `_subscribe_domain_change(...)` usage -- both are out of this phase's scope.
"""

from __future__ import annotations

import ast
import inspect

from src.application.runtime import build_desktop_api_registry
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _strip_strings_and_comments(source: str) -> str:
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


# ---------------------------------------------------------------------------
# 1. Producer -> bridge -> consumer graph: the four dead-bridge entries are gone
# ---------------------------------------------------------------------------


def test_bridge_specs_no_longer_routes_the_four_dead_entries():
    """`organizations_changed`/`auth_changed`/`employees_changed`/`departments_changed` each had
    zero real consumers of their bridge-routed `domain_changed` output (verified repo-wide: no
    `_subscribe_domain_change(...)` call filters entity_type "organization"/"user_account"/
    "employee"/"department") -- removed from the registry. Their own direct subscribers
    (admin_console binder, settings_workspace_controller, access_workspace_controller) never went
    through this bridge and are unaffected."""
    bridged_signal_names = {spec[0] for spec in domain_events._BRIDGE_SPECS}
    for dead in ("organizations_changed", "auth_changed", "employees_changed", "departments_changed"):
        assert dead not in bridged_signal_names, f"{dead} still routes through the generic bridge"


def test_the_four_signals_still_exist_with_their_own_direct_subscribers_unaffected():
    """Removing the dead bridge-routing entries must not touch the signals themselves -- they
    still exist and still have their own real, direct (non-bridge) consumers."""
    for signal_name in ("organizations_changed", "auth_changed", "employees_changed", "departments_changed"):
        assert hasattr(domain_events, signal_name), f"{signal_name} was deleted, not just un-bridged"


def test_shared_master_changed_signal_no_longer_exists():
    """Zero production consumers anywhere (only `domain_changed`, via
    `_subscribe_domain_change(...)`, was ever actually consumed) -- deleted entirely: field,
    `_build_bridge`'s emit branch, and its bridge-only test."""
    assert not hasattr(domain_events, "shared_master_changed")


def test_domain_changed_still_exists_with_real_production_consumers():
    """`domain_changed` itself is NOT dead -- dozens of still-unmodernized PM/Inventory
    controllers depend on it via `_subscribe_domain_change(...)` for entity types this phase never
    touches (project/tasks/costs/resources/baseline/register/timesheet/portfolio/inventory-* and
    the still-alive shared_master entries site/document/party/working_calendar). Per §5, only a
    generic signal with ZERO real production producers/consumers gets deleted -- this one does
    not qualify."""
    assert hasattr(domain_events, "domain_changed")
    seen = []
    domain_events.domain_changed.connect(seen.append)
    try:
        domain_events.project_changed.emit(_unique("p7-domain-changed-alive"))
    finally:
        domain_events.domain_changed.disconnect(seen.append)
    assert len(seen) == 1


def test_bridge_specs_still_routes_the_genuinely_alive_shared_master_entries():
    """`sites_changed`/`calendars_changed`/`documents_changed`/`parties_changed` remain bridged --
    Inventory's and PM's own `_subscribe_domain_change(..., scope_code="platform")` consumers
    genuinely depend on this (verified repo-wide)."""
    bridged_signal_names = {spec[0] for spec in domain_events._BRIDGE_SPECS}
    for alive in ("sites_changed", "calendars_changed", "documents_changed", "parties_changed"):
        assert alive in bridged_signal_names


# ---------------------------------------------------------------------------
# 2. Modernized capabilities: zero legacy-bridge presentation dependency
# ---------------------------------------------------------------------------


def test_organization_creation_never_touches_organizations_changed(services):
    """P5A: `create_organization` never emitted `organizations_changed` -- only
    `update_organization`/`set_active_organization` still do, for their own genuinely-unmodernized
    transitions."""
    catalog = _catalog(services)
    typed_calls = []
    catalog._organization_view_invalidation_adapter.organizationCollectionStale.connect(
        lambda: typed_calls.append("typed")
    )
    legacy_calls = []
    domain_events.organizations_changed.connect(lambda org_id: legacy_calls.append(org_id))

    services["organization_service"].create_organization(
        organization_code=_unique("P7-ORG"), display_name="P7 Organization"
    )

    assert typed_calls == ["typed"]
    assert legacy_calls == []


def test_module_entitlement_has_no_legacy_signal_at_all():
    """`modules_changed` was fully retired in P5B-3 -- not merely un-bridged, deleted entirely."""
    assert not hasattr(domain_events, "modules_changed")


def test_role_binding_has_no_legacy_signal_at_all():
    """RoleBinding never had its own module-level legacy signal (`access_changed` never existed
    for it) -- it went straight from the pre-existing `auth_changed`-adjacent world to typed
    events in P5C, with no intermediate bridge."""
    assert not hasattr(domain_events, "access_changed")
    assert not hasattr(domain_events, "role_binding_changed")


def test_tenant_membership_mutation_never_emits_auth_changed(services):
    """P5D: TenantMembership transitions collapse entirely into the typed
    TenantMembership{Activated,Suspended,Reactivated,Removed} -> ViewInvalidation path -- no
    `auth_changed` bridge was ever built for it."""
    from datetime import datetime, timedelta, timezone

    catalog = _catalog(services)
    typed_calls = []
    catalog._tenant_membership_view_invalidation_adapter.membershipDataStale.connect(
        lambda: typed_calls.append("typed")
    )

    # register_user() and authenticate() are themselves registration/session operations -- both
    # genuinely still-unmodernized `auth_changed` producers (confirmed: a successful login records
    # last-login metadata and emits `auth_changed` -- correct, unrelated behavior) -- so both must
    # run BEFORE the auth_changed probe is installed, to isolate what `accept_invitation` itself
    # (the actual TenantMembership transition under test) does on its own.
    target = services["auth_service"].register_user(
        _unique("p7-membership-target"), "P7Membership123!", display_name="P7 Membership Target"
    )
    admin_principal = services["user_session"].principal
    issued = services["tenant_membership_service"].issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    target_auth = services["auth_service"].authenticate(target.username, "P7Membership123!")
    services["user_session"].set_principal(services["auth_service"].build_principal(target_auth))

    auth_calls = []
    domain_events.auth_changed.connect(lambda user_id: auth_calls.append(user_id))
    services["tenant_membership_service"].accept_invitation(issued.token)
    services["user_session"].set_principal(admin_principal)

    assert typed_calls == ["typed"]
    assert auth_calls == []


def test_approval_has_no_legacy_signal_at_all():
    """`approvals_changed` was fully deleted in Approval-P3 -- confirmed still gone."""
    assert not hasattr(domain_events, "approvals_changed")


# ---------------------------------------------------------------------------
# 3. Representative still-unmodernized capability: auth/password, direct-wired, narrow
# ---------------------------------------------------------------------------


def test_password_reset_fires_auth_changed_and_only_the_narrow_access_workspace_reaction(services):
    """§18: a real operation on a genuinely still-unmodernized capability (password) ->
    `auth_changed` -> `AccessWorkspaceController._on_auth_changed` -> the narrow
    `_refresh_after_security_change()` reaction only -- never the full `refresh()`, never
    RoleBinding's/TenantMembership's own typed read models, never any other modernized
    capability's Qt adapter signal. (The mutation's own `on_success` callback ALSO calls
    `_refresh_after_security_change()` immediately, independent of the event path -- the same
    accepted "self-refresh after your own action" pattern already proven for Organization's own
    `createOrganization`; that is not double-counted here, only the *additional* signals this
    phase cares about.)"""
    _login(services, "admin", "ChangeMe123!")
    catalog = _catalog(services)
    access = catalog.adminAccessWorkspace
    access.ensureLoaded()

    target = services["auth_service"].register_user(
        _unique("p7-password-target"), "P7PasswordOld123!", display_name="P7 Password Target"
    )

    full_refresh_calls = []
    role_binding_calls = []
    organization_calls = []
    module_entitlement_calls = []
    approval_calls = []
    access.refresh = lambda: full_refresh_calls.append("refresh") or None
    catalog._role_binding_view_invalidation_adapter.roleBindingsStale.connect(
        lambda: role_binding_calls.append("stale")
    )
    catalog._organization_view_invalidation_adapter.organizationCollectionStale.connect(
        lambda: organization_calls.append("stale")
    )
    catalog._module_entitlement_view_invalidation_adapter.moduleEntitlementsStale.connect(
        lambda: module_entitlement_calls.append("stale")
    )
    catalog._approval_view_invalidation_adapter.approvalsStale.connect(
        lambda: approval_calls.append("stale")
    )
    auth_calls = []
    domain_events.auth_changed.connect(lambda user_id: auth_calls.append(user_id))

    result = access.forcePasswordReset(target.id)

    assert result["ok"] is True
    assert auth_calls == [target.id], "the still-unmodernized password capability must still emit its signal"
    assert full_refresh_calls == [], "auth_changed must never trigger the FULL Access workspace refresh"
    assert role_binding_calls == []
    assert organization_calls == []
    assert module_entitlement_calls == []
    assert approval_calls == []

    # Isolate `_on_auth_changed`'s OWN reaction (bypassing the mutation's own immediate
    # self-refresh): a fresh auth_changed emission alone must still only hit the narrow path.
    narrow_calls = []
    access._refresh_after_security_change = lambda: narrow_calls.append("security") or None
    domain_events.auth_changed.emit(target.id)
    assert narrow_calls == ["security"]
    assert full_refresh_calls == []


# ---------------------------------------------------------------------------
# 4. admin_console/domain_event_binder.py: real, non-compatibility, still-required responsibility
# ---------------------------------------------------------------------------


def test_admin_console_domain_event_binder_never_touches_the_generic_bridge():
    """§3: it subscribes directly to 8 specific legacy signals -- it never imports/uses
    `_subscribe_domain_change`, `domain_changed`, or `_BRIDGE_SPECS` at all. It already IS the
    §6-preferred "specific signal -> explicit consumer" shape; there is no compatibility-bridge
    responsibility here to delete."""
    import src.ui_qml.platform.controllers.admin_console.domain_event_binder as binder_module

    source = _strip_strings_and_comments(inspect.getsource(binder_module))
    for forbidden in ("_subscribe_domain_change", "domain_changed", "_BRIDGE_SPECS"):
        assert forbidden not in source


def test_admin_console_still_composite_refreshes_on_the_four_genuinely_unmodernized_signals(
    services,
):
    """The composite coalesced-refresh responsibility (9 sub-controllers, one refresh cycle) is
    real and still required for the update/activate-only slice of Organization plus
    Employees/Departments/Auth, none of which route through the (now-un-bridged) generic
    `domain_changed` mechanism -- confirmed via direct signal emission."""
    catalog = _catalog(services)
    admin = catalog.adminWorkspace
    refresh_calls = []
    admin.refresh = lambda: refresh_calls.append("refresh") or None

    domain_events.organizations_changed.emit(_unique("p7-admin-org"))
    domain_events.employees_changed.emit(_unique("p7-admin-emp"))
    domain_events.departments_changed.emit(_unique("p7-admin-dept"))
    domain_events.auth_changed.emit(_unique("p7-admin-auth"))

    assert refresh_calls == ["refresh", "refresh", "refresh", "refresh"]


# ---------------------------------------------------------------------------
# 5. PM Dashboard: Approval-P3's removal stays removed
# ---------------------------------------------------------------------------


def test_pm_dashboard_still_does_not_react_to_unrelated_capability_events(services):
    pm_catalog = _pm_catalog(services)
    dashboard = pm_catalog.dashboardWorkspace
    refresh_calls = []
    dashboard.refresh = lambda: refresh_calls.append("refresh")

    domain_events.organizations_changed.emit(_unique("p7-dashboard-org"))
    domain_events.auth_changed.emit(_unique("p7-dashboard-auth"))

    assert refresh_calls == []


# ---------------------------------------------------------------------------
# 6. Architecture guards
# ---------------------------------------------------------------------------


def test_no_generic_bridge_registry_exists_outside_domain_events_py():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or normalized.endswith("test_p7_legacy_bridge_removal.py"):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "_BRIDGE_SPECS" in _strip_strings_and_comments(source):
            hits.append(normalized)
    assert hits == ["src/core/shared/events/domain_events.py"], hits


def test_organization_service_create_never_emits_the_legacy_signal():
    import src.core.platform.application.master_data.org.organization_service as org_service_module

    source = _strip_strings_and_comments(
        inspect.getsource(org_service_module.OrganizationService.create_organization)
    )
    assert "organizations_changed" not in source


def test_approval_service_never_emits_the_deleted_legacy_signal():
    import src.core.platform.application.approval.approval_service as approval_service_module

    source = _strip_strings_and_comments(inspect.getsource(approval_service_module))
    assert "approvals_changed" not in source


def test_no_capability_mapper_imports_domain_events_or_qt():
    """The five typed-event -> ViewInvalidation mapper modules must never import the legacy
    `domain_events` hub or PySide6 -- no typed-event -> legacy bridge was built, in either
    direction."""
    mapper_modules = (
        "src.core.platform.application.master_data.org.event_handlers.view_invalidation",
        "src.core.platform.application.tenant.modules.event_handlers.view_invalidation",
        "src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation",
        "src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation",
        "src.core.platform.application.approval.event_handlers.view_invalidation",
    )
    import importlib

    for module_name in mapper_modules:
        module = importlib.import_module(module_name)
        tree = ast.parse(inspect.getsource(module))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        for forbidden in ("domain_events", "PySide6", "QtCore"):
            assert not any(forbidden in name for name in names), (module_name, names)


def test_no_wildcard_view_invalidation_listener_was_introduced():
    """No adapter (including admin_console/access) subscribes via `AllTenants`/
    `AnyOrganizationInTenant`, and no new "subscribe to everything, emit domain_changed" bridge
    was built on top of ViewInvalidation."""
    modules = (
        "src.ui_qml.platform.controllers.admin_console.domain_event_binder",
        "src.ui_qml.platform.controllers.identity_access.access.access_workspace_controller",
        "src.ui_qml.platform.context",
    )
    import importlib

    for module_name in modules:
        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("AllTenants", "AnyOrganizationInTenant", "ViewInvalidationHint"):
            assert forbidden not in source, (module_name, forbidden)


def test_no_service_locator_or_string_capability_router_introduced():
    for module_name in (
        "src.ui_qml.platform.context",
        "src.ui_qml.modules.project_management.context",
        "src.core.shared.events.domain_events",
    ):
        import importlib

        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("adapter_for(", "resolve_adapter(", "container.get(", "AdapterRegistry"):
            assert forbidden not in source


def test_p6_helper_responsibility_unchanged():
    """`ScopedViewInvalidationSubscription`'s public surface is exactly what P6 shipped -- P7 must
    not add wildcards/service-locator behavior/capability strings to it."""
    from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
        ScopedViewInvalidationSubscription,
    )

    replace_filter_params = set(
        inspect.signature(ScopedViewInvalidationSubscription.replace_filter).parameters
    )
    init_params = set(inspect.signature(ScopedViewInvalidationSubscription.__init__).parameters)
    dispose_params = set(inspect.signature(ScopedViewInvalidationSubscription.dispose).parameters)
    assert replace_filter_params == {"self", "filter"}
    assert init_params == {"self", "channel", "on_hint"}
    assert dispose_params == {"self"}
