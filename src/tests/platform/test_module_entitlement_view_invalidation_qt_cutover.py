"""P5B-3: the five Module Entitlement events (plus a direct provisioning-triggered case) mapped
onto `ViewInvalidationHint`, the one real Qt consumer (settings workspace's `moduleEntitlements`
list) migrated directly onto `ModuleEntitlementViewInvalidationAdapter`, and the legacy
`modules_changed` signal retired entirely -- no bridge. The other two former subscribers (control,
access workspaces) were traced end-to-end and found to read no module-entitlement-derived state
at all (incidental over-refresh from the coarse legacy signal) -- their subscriptions are simply
dropped, not migrated.

Uses the real `services` fixture (real Session, real UnitOfWorks, real composition-owned
`ViewInvalidationChannel`) plus the real `build_desktop_api_registry`/`PlatformWorkspaceCatalog`
construction, mirroring `test_organization_view_invalidation_qt_cutover.py`'s own pattern.
"""

from __future__ import annotations

import inspect

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.tenant.modules.event_handlers.view_invalidation import (
    MODULE_ENTITLEMENT_CATEGORY,
    MODULE_ENTITLEMENTS_SCOPE_CODE,
    build_module_entitlement_view_invalidation_handler,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicenseRevoked,
    ModuleLicensed,
    ModuleLifecycleTransitioned,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import ExactOrganization, OrganizationScope
from src.core.platform.infrastructure.persistence.module_entitlement_unit_of_work import (
    SqlAlchemyModuleEntitlementUnitOfWork,
)
from src.ui_qml.platform.adapters.module_entitlement_view_invalidation_adapter import (
    ModuleEntitlementViewInvalidationAdapter,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _active_tenant(services) -> str:
    return services["tenant_context_service"].get_active_tenant_id()


# ---------------------------------------------------------------------------
# Mapper: all five events -> the SAME target, exact scope, no extra hints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        ModuleLicensed(tenant_id="t-1", organization_id="o-1", module_code="project_management", occurred_at=None),
        ModuleLicenseRevoked(tenant_id="t-1", organization_id="o-1", module_code="project_management", occurred_at=None),
        ModuleEnabled(tenant_id="t-1", organization_id="o-1", module_code="project_management", occurred_at=None),
        ModuleDisabled(tenant_id="t-1", organization_id="o-1", module_code="project_management", occurred_at=None),
        ModuleLifecycleTransitioned(
            tenant_id="t-1", organization_id="o-1", module_code="project_management",
            previous_lifecycle_status="active", lifecycle_status="trial", occurred_at=None,
        ),
    ],
)
def test_mapper_produces_exactly_one_module_entitlements_hint_per_event(event):
    hints = []

    class _FakeChannel:
        def notify(self, hint):
            hints.append(hint)

    handler = build_module_entitlement_view_invalidation_handler(_FakeChannel())
    handler(event, DomainEventContext(correlation_id="corr-1"))

    assert len(hints) == 1
    hint = hints[0]
    assert hint.scope == OrganizationScope("t-1", "o-1")
    assert hint.category == MODULE_ENTITLEMENT_CATEGORY
    assert hint.scope_code == MODULE_ENTITLEMENTS_SCOPE_CODE
    assert hint.entity_type == "module_entitlement"


def _imported_module_names(module) -> set[str]:
    import ast

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_module_entitlement_view_invalidation_mapper_has_no_qt_dependency():
    import src.core.platform.application.tenant.modules.event_handlers.view_invalidation as mapper_module

    imports = _imported_module_names(mapper_module)
    for forbidden in ("PySide6", "QtCore", "ui_qml", "domain_events"):
        assert not any(forbidden in name for name in imports), imports


def test_module_entitlement_events_module_has_no_view_invalidation_or_ui_vocabulary():
    import src.core.platform.domain.tenant.modules.events as events_module

    imports = _imported_module_names(events_module)
    for forbidden in ("view_invalidation", "domain_events", "PySide6", "QtCore", "ui_qml"):
        assert not any(forbidden in name for name in imports), imports


# ---------------------------------------------------------------------------
# End-to-end: real semantic command -> real UI consumer refresh
# ---------------------------------------------------------------------------


def test_settings_workspace_module_entitlements_refresh_on_real_mutation(services):
    catalog = _catalog(services)
    catalog.settingsWorkspace.refresh()
    org = services["organization_service"].get_active_organization()

    services["module_catalog_service"].disable_module(org.id, "project_management")

    items = {row["id"]: row for row in catalog.settingsWorkspace.moduleEntitlements["items"]}
    assert items["project_management"]["state"]["runtimeEnabled"] is False


def test_access_workspace_no_longer_reacts_to_module_mutations(services):
    """P5B-3: `modules_changed` was dropped (not migrated) for Access workspace. Initial
    investigation suspected `scopeTypeOptions`' storeroom entry depended on
    `inventory_procurement`'s enablement (matching the fake QML-preview test helper's crafted
    data), but tracing the REAL desktop-API wiring end-to-end
    (`desktop_api_registry.py`'s `access_scope_type_choices`/`access_scope_option_loaders`) found
    the storeroom scope type is gated purely by whether the Inventory service object was composed
    at startup (`inventory_service is not None`), never by live module-entitlement state -- no
    read model in this workspace actually depends on it."""
    catalog = _catalog(services)
    catalog.adminAccessWorkspace.refresh()
    refresh_calls = []
    catalog.adminAccessWorkspace.refresh = lambda: refresh_calls.append("refresh")
    org = services["organization_service"].get_active_organization()

    services["module_catalog_service"].disable_module(org.id, "inventory_procurement")

    assert refresh_calls == []


def test_control_workspace_no_longer_reacts_to_module_mutations(services):
    """P5B-3: `modules_changed` was dropped (not migrated) for Control workspace -- traced
    end-to-end, its `refresh()` never reads module-entitlement state at all."""
    catalog = _catalog(services)
    catalog.controlWorkspace.ensureLoaded()
    refresh_calls = []
    catalog.controlWorkspace.refresh = lambda: refresh_calls.append("refresh")
    org = services["organization_service"].get_active_organization()

    services["module_catalog_service"].disable_module(org.id, "project_management")

    assert refresh_calls == []


def test_no_refresh_before_commit_and_none_on_rollback(services, monkeypatch):
    catalog = _catalog(services)
    catalog.settingsWorkspace.refresh()
    refresh_calls = []
    catalog.settingsWorkspace.refresh_module_entitlements = lambda: refresh_calls.append("refresh") or None
    org = services["organization_service"].get_active_organization()

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyModuleEntitlementUnitOfWork, "commit", _fail_commit)
    with pytest.raises(RuntimeError):
        services["module_catalog_service"].disable_module(org.id, "project_management")

    assert refresh_calls == []


def test_no_invalidation_on_no_op_command(services):
    catalog = _catalog(services)
    catalog.settingsWorkspace.refresh()
    refresh_calls = []
    catalog.settingsWorkspace.refresh_module_entitlements = lambda: refresh_calls.append("refresh") or None
    org = services["organization_service"].get_active_organization()

    services["module_catalog_service"].enable_module(org.id, "project_management")  # already enabled

    assert refresh_calls == []

    with pytest.raises(ValidationError):
        services["module_catalog_service"].enable_module(org.id, "hr_management")  # unlicensed -> rejected
    assert refresh_calls == []


# ---------------------------------------------------------------------------
# Non-active organization / cross-tenant
# ---------------------------------------------------------------------------


def test_non_active_organization_mutation_does_not_refresh_active_org_ui(services):
    organization_service = services["organization_service"]
    catalog = _catalog(services)
    catalog.settingsWorkspace.refresh()
    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-A2"), display_name="Qt Cutover Org A2", is_active=False
    )
    refresh_calls = []
    catalog.settingsWorkspace.refresh_module_entitlements = lambda: refresh_calls.append("refresh") or None

    services["module_catalog_service"].disable_module(org_a2.id, "project_management")

    assert organization_service.get_active_organization().id == org_a1.id
    assert refresh_calls == []


def test_command_against_a_foreign_tenant_organization_produces_no_invalidation(services):
    from src.core.platform.common.exceptions import NotFoundError
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM

    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)
    session = services["session"]
    hints = []
    channel.subscribe(ExactOrganization(tenant_a, "does-not-matter"), lambda hint: hints.append(hint))

    foreign_tenant_id = _unique_code("qtcut-tenant-foreign")
    session.add(
        TenantORM(id=foreign_tenant_id, tenant_code=_unique_code("QTF"), display_name="Foreign Tenant", is_active=True, version=1)
    )
    session.commit()
    foreign_org_id = _unique_code("qtcut-org-foreign")
    session.add(
        OrganizationORM(
            id=foreign_org_id, tenant_id=foreign_tenant_id, organization_code=_unique_code("QTFOREIGN"),
            display_name="Foreign Org", is_active=True, version=1,
        )
    )
    session.commit()

    with pytest.raises(NotFoundError):
        services["module_catalog_service"].disable_module(foreign_org_id, "project_management")

    assert hints == []


# ---------------------------------------------------------------------------
# Adapter: organization scope, no AllTenants/TenantWide
# ---------------------------------------------------------------------------


def test_adapter_only_reacts_to_its_exact_active_organization(services):
    channel = services["platform_view_invalidation_channel"]
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-SCOPE-A2"), display_name="Scope Org A2", is_active=False
    )

    adapter = ModuleEntitlementViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org_a1.id)
    signal_calls = []
    adapter.moduleEntitlementsStale.connect(lambda: signal_calls.append("stale"))

    services["module_catalog_service"].disable_module(org_a2.id, "project_management")
    assert signal_calls == []

    services["module_catalog_service"].disable_module(org_a1.id, "project_management")
    assert signal_calls == ["stale"]
    adapter.dispose()


def test_adapter_never_subscribes_via_all_tenants_or_tenant_wide(services):
    from src.core.shared.events.view_invalidation import AllTenants, TenantWide

    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    org = services["organization_service"].get_active_organization()

    adapter = ModuleEntitlementViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org.id)
    try:
        filters = [filt for filt, _handler in channel._subscriptions.values()]
        assert not any(isinstance(f, (AllTenants, TenantWide)) for f in filters)
        exact_filters = [f for f in filters if isinstance(f, ExactOrganization)]
        assert any(f.tenant_id == tenant_id and f.organization_id == org.id for f in exact_filters)
    finally:
        adapter.dispose()


# ---------------------------------------------------------------------------
# Switch lifecycle: organization switch and tenant switch, no stale/duplicate subscription
# ---------------------------------------------------------------------------


def test_adapter_follows_an_organization_switch_with_no_stale_or_duplicate_subscription(services):
    channel = services["platform_view_invalidation_channel"]
    organization_service = services["organization_service"]
    tenant_id = _active_tenant(services)
    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-SWITCH-A2"), display_name="Switch Org A2", is_active=False
    )

    adapter = ModuleEntitlementViewInvalidationAdapter(channel=channel, tenant_id=tenant_id, organization_id=org_a1.id)
    signal_calls = []
    adapter.moduleEntitlementsStale.connect(lambda: signal_calls.append("stale"))
    subscription_count_before = len(channel._subscriptions)

    services["module_catalog_service"].disable_module(org_a1.id, "project_management")
    assert signal_calls == ["stale"]

    organization_service.set_active_organization(org_a2.id)
    adapter.set_active_scope(tenant_id=tenant_id, organization_id=org_a2.id)
    assert len(channel._subscriptions) == subscription_count_before, (
        "switching must dispose the old subscription before adding the new one -- never accumulate"
    )

    # A1 is no longer the active organization's mutation target from the UI's perspective, and
    # the adapter no longer watches it.
    services["module_catalog_service"].enable_module(org_a1.id, "project_management")  # no-op anyway
    assert signal_calls == ["stale"]

    services["module_catalog_service"].disable_module(org_a2.id, "project_management")
    assert signal_calls == ["stale", "stale"]

    adapter.dispose()
    assert len(channel._subscriptions) == subscription_count_before - 1


def test_real_organization_switch_through_refresh_current_permissions_rewires_the_adapter(services):
    """True end-to-end proof through `PlatformWorkspaceCatalog.refreshCurrentPermissions()` (the
    real hook the QML shell calls after both a tenant and an organization switch), not a direct
    `adapter.set_active_scope(...)` call."""
    organization_service = services["organization_service"]
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    adapter = catalog._module_entitlement_view_invalidation_adapter

    org_a1 = organization_service.get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-REALSWITCH-A2"), display_name="Real Switch Org A2", is_active=False
    )

    def _current_filters():
        return [filt for filt, _handler in channel._subscriptions.values() if isinstance(filt, ExactOrganization)]

    assert any(f.organization_id == org_a1.id for f in _current_filters())

    organization_service.set_active_organization(org_a2.id)
    catalog.refreshCurrentPermissions()

    filters_after_switch = _current_filters()
    assert any(f.organization_id == org_a2.id for f in filters_after_switch)
    assert not any(f.organization_id == org_a1.id for f in filters_after_switch)
    assert adapter is catalog._module_entitlement_view_invalidation_adapter


def test_adapter_follows_a_tenant_switch_via_refresh_current_permissions(services):
    """A tenant switch also re-scopes the Module adapter (never leaves it pointed at the old
    tenant's organization) -- proven structurally, mirroring the Organization adapter's own
    tenant-switch test without requiring a live organization under the brand-new tenant."""
    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    tenant_a = _active_tenant(services)
    org_a1 = services["organization_service"].get_active_organization()

    def _current_filters():
        return [filt for filt, _handler in channel._subscriptions.values() if isinstance(filt, ExactOrganization)]

    assert any(f.tenant_id == tenant_a and f.organization_id == org_a1.id for f in _current_filters())

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("QTCUT-TENANT-B"), "Qt Cutover Tenant B")
    services["session"].flush()

    switch_result = catalog.tenantSwitcher.switchToTenant(tenant_b.id)
    assert switch_result["ok"] is True
    catalog.refreshCurrentPermissions()

    filters_after_switch = _current_filters()
    assert not any(f.tenant_id == tenant_a for f in filters_after_switch), (
        "the stale Tenant A/Org A1 subscription must be disposed after switching tenants"
    )


# ---------------------------------------------------------------------------
# Provisioning: direct ViewInvalidation when it targets the active organization, none otherwise
# ---------------------------------------------------------------------------


def test_provisioning_a_non_active_organization_produces_no_invalidation_and_no_events(services, monkeypatch):
    from src.core.shared.events.view_invalidation import AnyOrganizationInTenant

    app_service = services["platform_runtime_application_service"]
    catalog = services["module_catalog_service"]
    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    hints = []
    channel.subscribe(AnyOrganizationInTenant(tenant_id), lambda hint: hints.append(hint))

    recorded = []
    original_create = type(catalog._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event
        uow.record_event = lambda event: (recorded.append(event), original_record_event(event))[1]
        return uow

    monkeypatch.setattr(type(catalog._uow_factory), "create", _spy_create)

    app_service.provision_organization(
        organization_code=_unique_code("QTCUT-PROV-INACTIVE"),
        display_name="Provisioned Inactive Org",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=False,
        initial_module_codes=["project_management"],
    )

    assert recorded == []
    # `AnyOrganizationInTenant` also observes `OrganizationCreated`'s own unconditional
    # `organization_list`/`organization_details` hints (category="organization") -- filter to
    # this capability's own category, the thing this test actually verifies.
    assert [h for h in hints if h.category == MODULE_ENTITLEMENT_CATEGORY] == []


def test_provisioning_the_active_organization_produces_direct_invalidation_and_no_events(services, monkeypatch):
    """`provision_organization(is_active=True)` both creates AND activates the new organization
    in one call -- the module entitlement collection any open UI is showing just became stale
    (a different organization's rows are now the authoritative ones), so this legitimately
    produces direct ViewInvalidation, never a DomainEvent (P5B-SEM's provisioning-is-not-licensing
    decision, unchanged). Verified at the channel level with a broad, test-only
    `AnyOrganizationInTenant` subscription -- the provisioned organization's id does not exist
    until after this single call returns, so it cannot be known in advance the way
    `ExactOrganization` would require."""
    from src.core.shared.events.view_invalidation import AnyOrganizationInTenant

    app_service = services["platform_runtime_application_service"]
    catalog_service = services["module_catalog_service"]
    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)

    recorded = []
    original_create = type(catalog_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event
        uow.record_event = lambda event: (recorded.append(event), original_record_event(event))[1]
        return uow

    monkeypatch.setattr(type(catalog_service._uow_factory), "create", _spy_create)

    hints = []
    channel.subscribe(AnyOrganizationInTenant(tenant_id), lambda hint: hints.append(hint))

    code = _unique_code("QTCUT-PROV-ACTIVE")
    organization = app_service.provision_organization(
        organization_code=code,
        display_name="Provisioned Active Org",
        timezone_name="UTC",
        base_currency="EUR",
        is_active=True,
        initial_module_codes=["project_management"],
    )

    assert recorded == []
    module_hints = [h for h in hints if h.category == MODULE_ENTITLEMENT_CATEGORY]
    assert len(module_hints) == 1
    assert module_hints[0].scope == OrganizationScope(tenant_id, organization.id)
    assert module_hints[0].scope_code == MODULE_ENTITLEMENTS_SCOPE_CODE


def test_read_time_default_seeding_produces_no_invalidation_and_no_events(services):
    organization_service = services["organization_service"]
    catalog = services["module_catalog_service"]
    channel = services["platform_view_invalidation_channel"]
    tenant_id = _active_tenant(services)
    new_org = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-SEED"), display_name="Qt Cutover Seed Org", is_active=False
    )
    hints = []
    channel.subscribe(ExactOrganization(tenant_id, new_org.id), lambda hint: hints.append(hint))

    organization_service.set_active_organization(new_org.id)
    catalog.list_entitlements()  # triggers _ensure_context_default_rows' first-read row seeding

    assert hints == []
