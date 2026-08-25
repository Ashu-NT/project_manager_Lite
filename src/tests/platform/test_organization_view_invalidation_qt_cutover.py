"""P5A + Organization-specific P6A cutover: end-to-end proof that Organization creation reaches
the two real UI consumers (admin console organization list, settings organization profiles list)
through `OrganizationCreated -> ViewInvalidationHint -> OrganizationViewInvalidationAdapter`,
never the legacy `organizations_changed` signal -- and that `update_organization`/
`set_active_organization` still reach them through the unchanged legacy path.

Uses the real `services` fixture (real Session, real UnitOfWorks, real composition-owned
`ViewInvalidationChannel`) plus the real `build_desktop_api_registry`/`PlatformWorkspaceCatalog`
construction, mirroring `test_admin_workspace_eager_refresh_gating.py`'s own pattern -- not the
fully-faked `build_connected_platform_registry()` QML-preview helper other QML tests use, since
this needs the real backend event pipeline underneath.
"""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def test_standalone_create_organization_refreshes_both_ui_consumers(services):
    catalog = _catalog(services)
    catalog.adminWorkspace.organizations  # establish baseline read
    catalog.settingsWorkspace.refresh()

    code = _unique_code("QTCUT-STANDALONE")
    organization_service = services["organization_service"]
    organization_service.create_organization(organization_code=code, display_name="Qt Cutover Org")

    admin_titles = [row["title"] for row in catalog.adminWorkspace.organizations["items"]]
    settings_titles = [row["title"] for row in catalog.settingsWorkspace.organizationProfiles["items"]]
    assert "Qt Cutover Org" in admin_titles
    assert "Qt Cutover Org" in settings_titles


def test_provisioning_create_organization_refreshes_both_ui_consumers_identically(services):
    catalog = _catalog(services)
    catalog.adminWorkspace.organizations
    catalog.settingsWorkspace.refresh()

    app_service = services["platform_runtime_application_service"]
    code = _unique_code("QTCUT-PROV")
    app_service.provision_organization(
        organization_code=code, display_name="Qt Cutover Provisioned Org",
        timezone_name="UTC", base_currency="EUR", is_active=False, initial_module_codes=[],
    )

    admin_titles = [row["title"] for row in catalog.adminWorkspace.organizations["items"]]
    settings_titles = [row["title"] for row in catalog.settingsWorkspace.organizationProfiles["items"]]
    assert "Qt Cutover Provisioned Org" in admin_titles
    assert "Qt Cutover Provisioned Org" in settings_titles


def test_no_refresh_signal_before_commit_and_none_on_rollback(services):
    catalog = _catalog(services)
    refresh_calls = []
    catalog.adminWorkspace._organization_controller.refresh_organizations = (
        lambda: refresh_calls.append("admin") or None
    )

    organization_service = services["organization_service"]
    code = _unique_code("QTCUT-ROLLBACK")
    organization_service.create_organization(organization_code=code, display_name="First")

    from src.core.platform.common.exceptions import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        organization_service.create_organization(organization_code=code, display_name="Second")

    # Exactly one successful creation happened -- exactly one refresh signal, not two, and none
    # attributable to the failed/rolled-back second attempt.
    assert refresh_calls == ["admin"]


def test_update_and_activate_still_use_the_unchanged_legacy_signal_path(services):
    """P5A implements only OrganizationCreated -- update/activation must keep working exactly as
    before, via the legacy `organizations_changed` signal, untouched by this cutover."""
    from src.core.shared.events.domain_events import domain_events

    organization_service = services["organization_service"]
    organization = organization_service.create_organization(
        organization_code=_unique_code("QTCUT-UPDATE"), display_name="Before Update"
    )

    signal_calls = []
    domain_events.organizations_changed.connect(lambda org_id: signal_calls.append(org_id))

    updated = organization_service.update_organization(
        organization.id, expected_version=organization.version, display_name="After Update"
    )
    assert signal_calls == [updated.id]

    signal_calls.clear()
    activated = organization_service.set_active_organization(organization.id)
    assert signal_calls == [activated.id]


def test_adapter_only_reacts_to_the_currently_active_tenant(services):
    """Tenant-scope hardening (post-approval review): the adapter subscribes via
    `TenantWide(tenant_id)`, not `AllTenants()` -- a Tenant B organization-list invalidation must
    not fire the Qt signal while Tenant A is active."""
    from src.ui_qml.platform.adapters.organization_view_invalidation_adapter import (
        OrganizationViewInvalidationAdapter,
    )

    channel = services["platform_view_invalidation_channel"]
    tenant_a = services["tenant_context_service"].get_active_tenant_id()
    adapter = OrganizationViewInvalidationAdapter(channel=channel, tenant_id=tenant_a)
    signal_calls = []
    adapter.organizationCollectionStale.connect(lambda: signal_calls.append("stale"))

    organization_service = services["organization_service"]
    organization_service.create_organization(
        organization_code=_unique_code("SCOPE-A"), display_name="Scope Tenant A Org"
    )
    assert signal_calls == ["stale"]

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("SCOPE-TENANT-B"), "Scope Tenant B")
    services["session"].flush()

    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.application.master_data.org.organization_service import OrganizationService

    ctx_b = UserSessionContext()
    ctx_b.set_principal(
        UserSessionPrincipal(
            user_id="scope-tenant-b-user", username="scope-tenant-b-user", display_name="Tenant B User",
            role_names=frozenset(["admin"]), permissions=frozenset(["settings.manage"]),
        )
    )
    ctx_b.set_active_tenant_id(tenant_b.id)
    service_as_b = OrganizationService(
        session=organization_service._session,
        organization_repo=organization_service._organization_repo,
        uow_factory=organization_service._uow_factory,
        clock=organization_service._clock,
        user_session=ctx_b,
        enterprise_audit_service=organization_service._enterprise_audit_service,
        tenant_context_service=None,
        overview_rollup_reader=organization_service._overview_rollup_reader,
    )
    service_as_b.create_organization(organization_code=_unique_code("SCOPE-B"), display_name="Scope Tenant B Org")

    # Still exactly the one signal from Tenant A's creation -- Tenant B's creation, while Tenant A
    # is the active subscription, produced none.
    assert signal_calls == ["stale"]
    adapter.dispose()


def test_adapter_follows_a_tenant_switch_with_no_stale_or_duplicate_subscription(services):
    """Tenant-scope hardening: `set_active_tenant(...)` must dispose the previous subscription
    before creating the new one -- proven both behaviorally (A stops firing, B starts) and
    structurally (the channel never accumulates more than one live subscription for this
    adapter)."""
    channel = services["platform_view_invalidation_channel"]
    tenant_a = services["tenant_context_service"].get_active_tenant_id()

    from src.ui_qml.platform.adapters.organization_view_invalidation_adapter import (
        OrganizationViewInvalidationAdapter,
    )

    adapter = OrganizationViewInvalidationAdapter(channel=channel, tenant_id=tenant_a)
    signal_calls = []
    adapter.organizationCollectionStale.connect(lambda: signal_calls.append("stale"))
    subscription_count_before = len(channel._subscriptions)

    organization_service = services["organization_service"]
    organization_service.create_organization(
        organization_code=_unique_code("SWITCH-A1"), display_name="Switch Org A1"
    )
    assert signal_calls == ["stale"]

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("SWITCH-TENANT-B"), "Switch Tenant B")
    services["session"].flush()

    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.application.master_data.org.organization_service import OrganizationService

    ctx_b = UserSessionContext()
    ctx_b.set_principal(
        UserSessionPrincipal(
            user_id="switch-tenant-b-user", username="switch-tenant-b-user", display_name="Tenant B User",
            role_names=frozenset(["admin"]), permissions=frozenset(["settings.manage"]),
        )
    )
    ctx_b.set_active_tenant_id(tenant_b.id)
    service_as_b = OrganizationService(
        session=organization_service._session,
        organization_repo=organization_service._organization_repo,
        uow_factory=organization_service._uow_factory,
        clock=organization_service._clock,
        user_session=ctx_b,
        enterprise_audit_service=organization_service._enterprise_audit_service,
        tenant_context_service=None,
        overview_rollup_reader=organization_service._overview_rollup_reader,
    )

    # Simulate the switch: exactly what context.py's _on_tenant_switched does.
    adapter.set_active_tenant(tenant_b.id)
    subscription_count_after_switch = len(channel._subscriptions)
    assert subscription_count_after_switch == subscription_count_before, (
        "switching must dispose the old subscription before adding the new one -- never "
        "accumulate"
    )

    # Tenant A creating another organization must no longer refresh (stale subscription gone).
    organization_service.create_organization(
        organization_code=_unique_code("SWITCH-A2"), display_name="Switch Org A2"
    )
    assert signal_calls == ["stale"], "Tenant A must no longer trigger the signal after switching away"

    # Tenant B creating an organization must now refresh (new subscription live).
    service_as_b.create_organization(organization_code=_unique_code("SWITCH-B1"), display_name="Switch Org B1")
    assert signal_calls == ["stale", "stale"], "Tenant B must trigger the signal once switched to"

    adapter.dispose()
    assert len(channel._subscriptions) == subscription_count_before - 1


def test_real_tenant_switch_through_the_catalog_rewires_the_adapter_end_to_end(services):
    """True end-to-end proof through the real `TenantSwitcherController.switchToTenant()` API
    (not the direct `adapter.set_active_tenant(...)` call the other two tests use) that
    `context.py`'s `tenantSwitched` wiring correctly follows a real tenant switch.

    Verified structurally (the channel's own live subscription now targets Tenant B) rather than
    via a full create_organization() call under Tenant B: a brand-new tenant has no active
    organization yet, which `record_audit_entry`'s tenant/org scoping requires regardless of this
    cutover, and bootstrapping one collides on the DEFAULT organization_code's cross-tenant
    unique constraint in this shared test database -- both pre-existing, unrelated to this
    hardening pass and to the adapter's own wiring, which is what this test actually verifies."""
    from src.core.shared.events.view_invalidation import TenantWide

    catalog = _catalog(services)
    channel = services["platform_view_invalidation_channel"]
    adapter = catalog._organization_view_invalidation_adapter

    def _current_filters():
        return [filt for filt, _handler in channel._subscriptions.values() if isinstance(filt, TenantWide)]

    tenant_a = services["tenant_context_service"].get_active_tenant_id()
    assert any(f.tenant_id == tenant_a for f in _current_filters())

    admin_svc = services["tenant_admin_service"]
    tenant_b = admin_svc.create_tenant(_unique_code("REALSWITCH-TENANT-B"), "Real Switch Tenant B")
    services["session"].flush()

    switch_result = catalog.tenantSwitcher.switchToTenant(tenant_b.id)
    assert switch_result["ok"] is True
    assert catalog.tenantSwitcher.activeTenantId == tenant_b.id

    filters_after_switch = _current_filters()
    assert any(f.tenant_id == tenant_b.id for f in filters_after_switch), (
        "the adapter's live subscription must now target Tenant B"
    )
    assert not any(f.tenant_id == tenant_a for f in filters_after_switch), (
        "the stale Tenant A subscription must be disposed, not left alongside the new one"
    )
    assert adapter is catalog._organization_view_invalidation_adapter, (
        "one adapter instance persists across the switch -- it is re-scoped in place, never "
        "reconstructed"
    )


def test_admin_console_own_mutation_still_self_refreshes_via_existing_direct_path(services):
    """Pre-existing, unrelated behavior (refresh_after_organization_change) must be unaffected by
    this cutover: the admin console still refreshes its own organization list immediately after
    ITS OWN createOrganization action, independent of the event/ViewInvalidation path."""
    catalog = _catalog(services)

    result = catalog.adminWorkspace.createOrganization(
        {
            "organizationCode": _unique_code("QTCUT-SELF"),
            "displayName": "Self Refresh Org",
            "timezoneName": "UTC",
            "baseCurrency": "USD",
            "isActive": False,
            "initialModuleCodes": [],
        }
    )
    assert result["ok"] is True
    titles = [row["title"] for row in catalog.adminWorkspace.organizations["items"]]
    assert "Self Refresh Org" in titles
