"""Guards against reintroducing a generic legacy-compatibility bridge
(`_BRIDGE_SPECS`/`_wire_bridges`/`domain_changed`/`DomainChangeEvent`/`shared_master_changed`/
`_subscribe_domain_change`). Every capability wires its own typed ViewInvalidation adapter
directly; nothing is routed through a generic entity_type/scope_code dispatch table."""

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
# 1. The entire generic bridge mechanism is gone -- not merely 4 dead entries
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 2. Modernized capabilities: zero legacy-bridge presentation dependency
# ---------------------------------------------------------------------------


def test_organization_creation_produces_exactly_the_typed_view_invalidation(services):
    catalog = _catalog(services)
    typed_calls = []
    catalog._organization_view_invalidation_adapter.organizationCollectionStale.connect(
        lambda: typed_calls.append("typed")
    )

    services["organization_service"].create_organization(
        organization_code=_unique("P7-ORG"), display_name="P7 Organization"
    )

    assert typed_calls == ["typed"]


def test_tenant_membership_mutation_produces_exactly_the_typed_view_invalidation(services):
    """`accept_invitation` produces exactly one typed `tenant_membership` invalidation."""
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


# ---------------------------------------------------------------------------
# 2b. Representative direct-wiring proofs across PM, Inventory, and shared-master
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


# ---------------------------------------------------------------------------
# 3. Auth/Security: direct-wired, narrow
# ---------------------------------------------------------------------------


def test_password_reset_produces_exactly_the_typed_account_security_invalidation(services):
    """Password reset records the typed `PasswordChanged` event, mapped to the
    `account_security` ViewInvalidation category: only that narrow target reacts; the Access
    workspace's FULL refresh and every other target stay untouched."""
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


# ---------------------------------------------------------------------------
# 6. Architecture guards
# ---------------------------------------------------------------------------


def test_no_generic_bridge_registry_exists_anywhere():
    """`_BRIDGE_SPECS` and the legacy `domain_events.py` module it once lived in are both gone
    entirely."""
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
    """A signal-name-string -> registry -> generic callback under any name would just rename
    `_BRIDGE_SPECS`."""
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
    `AnyOrganizationInTenant`, and no new "subscribe to everything" bridge was built on top of
    ViewInvalidation."""
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
    """`ScopedViewInvalidationSubscription`'s public surface stays minimal -- no
    wildcards/service-locator behavior/capability strings."""
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
