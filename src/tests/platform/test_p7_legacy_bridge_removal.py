"""P7 + P7A: pre-release removal of the ENTIRE generic legacy-compatibility bridge architecture
(`_BRIDGE_SPECS`/`_wire_bridges`/`domain_changed`/`DomainChangeEvent`/`shared_master_changed`/
`_subscribe_domain_change`) -- not merely the residue for the five already-modernized capabilities
(P7's original, narrower scope), but the entire mechanism (P7A). Every still-unmodernized
capability (PM/Inventory module signals, auth-adjacent Platform signals) is now direct-wired:
`domain_events.<specific_signal>.connect(callback)`, never routed through a generic entity_type/
scope_code dispatch table.

`admin_console/domain_event_binder.py` was never part of the bridge in the first place (proven in
P7: it subscribes directly to 8 specific signals) -- kept unchanged, still real, non-compatibility
composite-refresh coordination.
"""

from __future__ import annotations

import ast
import inspect

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
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


def _inventory_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


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
# 1. P7A: the entire generic bridge mechanism is gone -- not merely 4 dead entries
# ---------------------------------------------------------------------------


# P46B: `test_bridge_specs_no_longer_exists_at_all`/`test_domain_changed_signal_no_longer_exists`/
# `test_shared_master_changed_signal_no_longer_exists`/`test_domain_change_event_class_no_longer_
# exists`/`test_wire_bridges_no_longer_exists` (standalone `hasattr(domain_events, ...)` checks)
# removed -- `domain_events`/`DomainEvents` is deleted outright. `test_no_generic_bridge_registry_
# exists_anywhere` below, and `test_deleted_bridge_and_dead_signal_names_have_zero_production_
# references` in test_p8_platform_event_architecture_canonicalization.py, independently prove zero
# production references for `_BRIDGE_SPECS`/`domain_changed`/`shared_master_changed`/
# `DomainChangeEvent`/`_wire_bridges`/`_build_bridge` across all production source -- a strictly
# stronger guarantee than a runtime `hasattr` check on one (now-deleted) object.


def test_subscribe_domain_change_no_longer_exists_on_any_controller_base():
    import src.ui_qml.modules.inventory_procurement.controllers.common.workspace_controller_base as inv_base
    import src.ui_qml.modules.project_management.controllers.common.workspace_controller_base as pm_base
    import src.ui_qml.platform.controllers.common.workspace_controller_base as platform_base

    for module, cls_name in (
        (platform_base, "PlatformWorkspaceControllerBase"),
        (pm_base, "ProjectManagementWorkspaceControllerBase"),
        (inv_base, "InventoryProcurementWorkspaceControllerBase"),
    ):
        cls = getattr(module, cls_name)
        assert not hasattr(cls, "_subscribe_domain_change")


# P46B: `test_zero_legacy_signals_remain_on_domain_events` (this pass's own interim guard, added
# when `DomainEvents` was emptied but not yet deleted) is superseded now that the module is deleted
# outright -- see test_p8_platform_event_architecture_canonicalization.py's `_current_signal_
# names`/`test_zero_pm_legacy_signal_fields_remain` for the permanent "zero legacy signals
# application-wide" guard.


# ---------------------------------------------------------------------------
# 2. Modernized capabilities: zero legacy-bridge presentation dependency
# ---------------------------------------------------------------------------


def test_organization_creation_produces_exactly_the_typed_view_invalidation(services):
    """P5A proved `create_organization` never emitted `organizations_changed`, back when
    `update_organization`/`set_active_organization` still did for their own then-unmodernized
    transitions. P10D modernized those too and deleted the legacy signal entirely (see
    `test_organizations_changed_field_no_longer_exists` in test_p7b_dead_signal_cleanup.py and
    `test_organization_has_no_legacy_signal_at_all` in
    test_p8_platform_event_architecture_canonicalization.py) -- this test now only proves the
    positive: creation still produces exactly the one typed `organization_list` invalidation."""
    catalog = _catalog(services)
    typed_calls = []
    catalog._organization_view_invalidation_adapter.organizationCollectionStale.connect(
        lambda: typed_calls.append("typed")
    )

    services["organization_service"].create_organization(
        organization_code=_unique("P7-ORG"), display_name="P7 Organization"
    )

    assert typed_calls == ["typed"]


# P46B: `test_module_entitlement_has_no_legacy_signal_at_all` (`modules_changed`, retired P5B-3)
# and `test_role_binding_has_no_legacy_signal_at_all` (`access_changed`/`role_binding_changed`,
# never existed for RoleBinding at all) removed -- both were standalone `hasattr(domain_events,
# ...)` checks; `domain_events` is deleted outright.


def test_tenant_membership_mutation_produces_exactly_the_typed_view_invalidation(services):
    """P5D: TenantMembership transitions collapse entirely into the typed
    TenantMembership{Activated,Suspended,Reactivated,Removed} -> ViewInvalidation path.
    P46B: `auth_changed` no longer exists at all (Auth/Security is itself now fully modernized),
    so there is no legacy signal left to prove this doesn't also emit -- this now only proves the
    positive: `accept_invitation` produces exactly the one typed `tenant_membership` invalidation."""
    from datetime import datetime, timedelta, timezone

    catalog = _catalog(services)
    typed_calls = []
    catalog._tenant_membership_view_invalidation_adapter.membershipDataStale.connect(
        lambda: typed_calls.append("typed")
    )

    target = services["auth_service"].register_user(
        _unique("p7-membership-target"), "P7Membership123!", display_name="P7 Membership Target"
    )
    admin_principal = services["user_session"].principal
    issued = services["tenant_membership_service"].issue_invitation(
        target.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    target_auth = services["auth_service"].authenticate(target.username, "P7Membership123!")
    services["user_session"].set_principal(services["auth_service"].build_principal(target_auth))

    services["tenant_membership_service"].accept_invitation(issued.token)
    services["user_session"].set_principal(admin_principal)

    assert typed_calls == ["typed"]


# P46B: `test_approval_has_no_legacy_signal_at_all` (`approvals_changed`, deleted Approval-P3)
# removed -- standalone `hasattr(domain_events, ...)` check; `domain_events` is deleted outright.


# ---------------------------------------------------------------------------
# 2b. §21: representative direct-wiring proofs across PM, Inventory, and shared-master
# ---------------------------------------------------------------------------


def test_pm_register_workspace_direct_wired_to_project_stale_exactly_once(services):

    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.registerWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    pm_catalog._register_project_view_invalidation_adapter.projectListStale.emit(
        _unique("p43-register")
    )

    assert refresh_calls == ["refresh"]


# P46B: `test_pm_register_workspace_does_not_react_to_an_unrelated_signal` used `auth_changed` as
# its "some other module's still-legacy signal" stand-in (P33/P36/P37/P38B/P39 had each already
# retired the previous stand-in in turn). Auth/Security is now itself fully modernized -- there is
# no legacy Signal field left anywhere in the application to construct this proof from at all
# (see `test_zero_legacy_signals_remain_on_domain_events` above). The property it protected --
# direct ViewInvalidation wiring never widens scope to an unrelated module -- is now a structural
# guarantee of the ViewInvalidation channel's own scope/category filtering, not something a signal
# emission can accidentally leak through; it stays covered by each adapter's own dedicated
# scope-filter tests (e.g. this file's own precision tests below, and each capability's own
# `event_handlers/view_invalidation.py` mapping tests).


def test_inventory_dashboard_direct_wired_to_every_inventory_signal(services):
    inventory_catalog = _inventory_catalog(services)
    controller = inventory_catalog.dashboardWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    inventory_catalog._dashboard_catalog_view_invalidation_adapter.itemListStale.emit(
        _unique("p7a-inv-item")
    )
    inventory_catalog._dashboard_purchase_order_view_invalidation_adapter.purchaseOrderListStale.emit(
        _unique("p7a-inv-po")
    )

    assert refresh_calls == ["refresh", "refresh"]


# P46B: `test_inventory_dashboard_does_not_react_to_an_unrelated_shared_master_signal` and
# `test_inventory_catalog_workspace_does_not_react_to_an_unrelated_shared_master_signal` both used
# `auth_changed` as the "genuinely unrelated shared-master signal" stand-in -- removed for the same
# reason as the PM equivalent above: there is no legacy Signal field left anywhere to construct
# this proof from, and the isolation property itself is now structural (ViewInvalidation scope/
# category filtering), not something dependent on any one signal's continued existence.


# ---------------------------------------------------------------------------
# 3. Auth/Security: fully modernized, direct-wired, narrow (P46B)
# ---------------------------------------------------------------------------


def test_password_reset_produces_exactly_the_typed_account_security_invalidation(services):
    """P46B: password reset (`force_password_reset`) is now fully modernized -- it records the
    typed `PasswordChanged` event, mapped to the `account_security` ViewInvalidation category
    (replacing the legacy `auth_changed` Signal this test previously exercised). Proves the same
    isolation property as before: only the narrow `account_security` target reacts; the Access
    workspace's own FULL refresh, and every other unrelated ViewInvalidation target, stay
    untouched."""
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
    account_security_calls = []
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
    catalog._account_security_view_invalidation_adapter.accountSecurityStale.connect(
        lambda: account_security_calls.append("stale")
    )

    result = access.forcePasswordReset(target.id)

    assert result["ok"] is True
    assert account_security_calls == ["stale"], "PasswordChanged must reach the account_security target"
    assert full_refresh_calls == [], "account_security invalidation must never trigger the FULL Access workspace refresh"
    assert role_binding_calls == []
    assert organization_calls == []
    assert module_entitlement_calls == []
    assert approval_calls == []


# P46B: `test_admin_console_domain_event_binder_never_touches_the_generic_bridge` and
# `test_admin_console_still_composite_refreshes_on_the_one_genuinely_unmodernized_signal` are
# removed -- `admin_console/domain_event_binder.py` (the composite `auth_changed`-among-8-signals
# coarse refresher) is deleted outright, not merely unused: the admin console now reacts to the
# narrow `account_security` target (`refresh_after_account_security_change`) and the pre-existing
# narrow `refresh_users` target, never a coarse full refresh. See
# `test_zero_auth_changed_subscribers_remain` in test_p5_closeout_auth_changed_audit.py for the
# module-deletion guard.


# P46B: `test_pm_dashboard_still_does_not_react_to_unrelated_capability_events` used `auth_changed`
# as its "unrelated capability event" vehicle -- removed for the same reason as the other
# auth_changed-as-stand-in isolation tests above; there is no legacy Signal left to construct it
# from, and the underlying isolation guarantee is structural (ViewInvalidation scope/category
# filtering), covered by each capability's own dedicated tests.


# ---------------------------------------------------------------------------
# 6. Architecture guards
# ---------------------------------------------------------------------------


def test_no_generic_bridge_registry_exists_anywhere():
    """P7A: `_BRIDGE_SPECS` is gone entirely. P46B: the legacy `domain_events.py` module it once
    lived in is deleted outright."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or normalized.endswith((
            "test_p7_legacy_bridge_removal.py", "test_p7b_dead_signal_cleanup.py",
            "test_p8_platform_event_architecture_canonicalization.py",
            "test_p10d_organization_event_modernization.py",
        )):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "_BRIDGE_SPECS" in _strip_strings_and_comments(source):
            hits.append(normalized)
    assert hits == [], hits


def test_no_replacement_generic_router_or_registry_introduced():
    """§7/§23: forbidden replacement shapes -- a signal-name-string -> registry -> generic
    callback under any name would just rename `_BRIDGE_SPECS`."""
    import glob

    forbidden_names = (
        "LegacySignalRouter",
        "DomainSignalRegistry",
        "EntityChangeRouter",
        "SignalDispatchMap",
        "CapabilitySignalRegistry",
    )
    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or normalized.endswith((
            "test_p7_legacy_bridge_removal.py",
            "test_p8_platform_event_architecture_canonicalization.py",
        )):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if any(name in source for name in forbidden_names):
            hits.append(normalized)
    assert hits == [], hits


def test_subscribe_domain_change_has_zero_production_references():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if "_subscribe_domain_change" in source:
            hits.append(normalized)
    assert hits == [], hits


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
    was built on top of ViewInvalidation. P46B: `admin_console/domain_event_binder.py` is deleted
    outright, so it is no longer part of this module inventory at all."""
    modules = (
        "src.ui_qml.platform.controllers.admin_console.admin_console_controller",
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
    ):
        import importlib

        module = importlib.import_module(module_name)
        source = _strip_strings_and_comments(inspect.getsource(module))
        for forbidden in ("adapter_for(", "resolve_adapter(", "container.get(", "AdapterRegistry"):
            assert forbidden not in source


def test_p6_helper_responsibility_unchanged():
    """`ScopedViewInvalidationSubscription`'s public surface is exactly what P6 shipped -- P7 must
    not add wildcards/service-locator behavior/capability strings to it."""
    from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
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
