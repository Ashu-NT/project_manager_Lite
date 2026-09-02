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
from src.core.shared.events.domain_events import domain_events
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


def test_bridge_specs_no_longer_exists_at_all():
    assert not hasattr(domain_events, "_BRIDGE_SPECS")
    assert not hasattr(domain_events.__class__, "_BRIDGE_SPECS")


def test_domain_changed_signal_no_longer_exists():
    assert not hasattr(domain_events, "domain_changed")


def test_shared_master_changed_signal_no_longer_exists():
    assert not hasattr(domain_events, "shared_master_changed")


def test_domain_change_event_class_no_longer_exists():
    import src.core.shared.events.domain_events as domain_events_module

    assert not hasattr(domain_events_module, "DomainChangeEvent")


def test_wire_bridges_no_longer_exists():
    assert not hasattr(domain_events, "_wire_bridges")
    assert not hasattr(domain_events, "_build_bridge")


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


def test_all_still_unmodernized_signals_survive_with_real_direct_consumers():
    """`organizations_changed`/`employees_changed`/`departments_changed`/`sites_changed`/
    `parties_changed`/`documents_changed` are deliberately absent from this list (P10D, P12B,
    P13B, P14B, P15B, P16D): all six capabilities are now fully modernized (create/profile events
    are typed), so their legacy signals were actually deleted, not merely left un-bridged like
    the ones below. `inventory_items_changed`/`inventory_item_categories_changed` are likewise
    deliberately absent -- P24 fully modernized Item Catalog + Item Category. `resources_changed`
    is ALSO deliberately absent (P35-CLEANUP correction) -- P18A/P18B fully modernized Project
    Resource (`ResourceMasterChanged`/`ResourceCapabilityChanged`, canonical ViewInvalidation),
    so it was actually deleted too; see `test_resources_changed_field_is_absent_from_domain_events`
    in `test_p18b_resource_view_invalidation.py` for the dedicated retirement proof."""

    for signal_name in (
        "auth_changed",
        "project_changed", "tasks_changed",
    ):
        assert hasattr(domain_events, signal_name), f"{signal_name} was deleted, not just un-bridged"


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
# 2b. §21: representative direct-wiring proofs across PM, Inventory, and shared-master
# ---------------------------------------------------------------------------


def test_pm_register_workspace_direct_wired_to_register_changed_exactly_once(services):
    """PM's register binder now connects directly to `register_changed`/`project_changed` --
    no generic `domain_changed` involved."""
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.registerWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.register_changed.emit(_unique("p7a-register"))

    assert refresh_calls == ["refresh"]


def test_pm_register_workspace_does_not_react_to_an_unrelated_signal(services):
    """Direct wiring must not accidentally widen scope -- an unrelated other-module signal must
    never reach a PM controller.

    P33-CLEANUP: was `..._an_unrelated_inventory_signal`, emitting `inventory_balances_changed`
    (deleted at P31B). Inventory/Procurement now has ZERO legacy Signal fields (P33) -- there is
    no longer any Inventory signal left to use as the "unrelated" example, so this now uses a
    still-legacy Finance signal instead, preserving the same cross-module-isolation property."""
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.registerWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.commitments_changed.emit(_unique("p7a-unrelated-finance"))

    assert refresh_calls == []


def test_inventory_dashboard_direct_wired_to_every_inventory_signal(services):
    """Inventory's dashboard binder now connects directly to every still-legacy inventory-module
    signal -- no generic `scope_code="inventory_procurement"` bridge filter involved.
    `inventory_items_changed` is gone (P24): Dashboard's real Item dependency (low-stock row
    labels) now reaches it through `InventoryCatalogViewInvalidationAdapter.itemListStale`,
    proven separately alongside the remaining direct-wired legacy signal. `inventory_purchase_
    orders_changed` is gone too (P28B): Dashboard's real PO/Requisition/Balance KPI dependency
    now reaches it through `PurchaseOrderViewInvalidationAdapter.purchaseOrderListStale`."""
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


def test_inventory_dashboard_does_not_react_to_an_unrelated_pm_signal(services):
    inventory_catalog = _inventory_catalog(services)
    controller = inventory_catalog.dashboardWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.project_changed.emit(_unique("p7a-unrelated-pm"))

    assert refresh_calls == []


# P16D removed `test_inventory_catalog_workspace_direct_wired_to_shared_master_document`:
# Catalog's binder no longer subscribes to `documents_changed` at all -- Document changes now
# reach this workspace only through the narrow `refresh_document_options()`/
# `refresh_selected_item_linked_documents()` typed-event paths, not this composite signal. See
# test_p16d_document_link_typed_events.py.


def test_inventory_catalog_workspace_does_not_react_to_an_unrelated_shared_master_signal(services):
    """`auth_changed` is a real shared-master signal, but NOT one the catalog workspace's own
    binder ever subscribed to -- direct wiring must preserve that exact per-consumer scope, not
    widen it."""
    inventory_catalog = _inventory_catalog(services)
    controller = inventory_catalog.catalogWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.auth_changed.emit(_unique("p7a-unrelated-auth"))

    assert refresh_calls == []


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


def test_admin_console_still_composite_refreshes_on_the_one_genuinely_unmodernized_signal(
    services,
):
    """Organization, Employee, Department, Site, and Party are no longer in this list (P10D, P12B,
    P13B, P14B, P15B): all five are fully modernized and route through their own typed
    ViewInvalidation targets instead."""
    catalog = _catalog(services)
    admin = catalog.adminWorkspace
    refresh_calls = []
    admin.refresh = lambda: refresh_calls.append("refresh") or None

    domain_events.auth_changed.emit(_unique("p7-admin-auth"))

    assert refresh_calls == ["refresh"]


# ---------------------------------------------------------------------------
# 5. PM Dashboard: Approval-P3's removal stays removed
# ---------------------------------------------------------------------------


def test_pm_dashboard_still_does_not_react_to_unrelated_capability_events(services):
    pm_catalog = _pm_catalog(services)
    dashboard = pm_catalog.dashboardWorkspace
    refresh_calls = []
    dashboard.refresh = lambda: refresh_calls.append("refresh")

    domain_events.auth_changed.emit(_unique("p7-dashboard-auth"))

    assert refresh_calls == []


# ---------------------------------------------------------------------------
# 6. Architecture guards
# ---------------------------------------------------------------------------


def test_no_generic_bridge_registry_exists_anywhere():
    """P7A: `_BRIDGE_SPECS` is gone entirely -- not even domain_events.py itself references it
    any more."""
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
