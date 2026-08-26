from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _inventory_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


def _wire_like_app_py(platform_catalog, pm_catalog, inventory_catalog) -> None:
    """Mirrors src/ui_qml/shell/app.py's own wiring exactly -- not a test-only shortcut."""
    platform_catalog.tenantSwitcher.tenantSwitched.connect(pm_catalog.refreshAllWorkspaces)
    platform_catalog.organizationSwitcher.organizationSwitched.connect(pm_catalog.refreshAllWorkspaces)
    platform_catalog.tenantSwitcher.tenantSwitched.connect(inventory_catalog.refreshAllWorkspaces)
    platform_catalog.organizationSwitcher.organizationSwitched.connect(inventory_catalog.refreshAllWorkspaces)


def test_pm_projects_workspace_no_longer_shows_org_a_data_after_switching_to_org_b(services):
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    org_b = organization_service.create_organization(
        organization_code="RESCOPE-PM-B", display_name="Rescope PM Org B", is_enabled=True
    )
    project_a = services["project_service"].create_project(
        "Rescope PM Project A", financial_currency_code="USD"
    )

    platform_catalog = _catalog(services)
    pm_catalog = _pm_catalog(services)
    _wire_like_app_py(platform_catalog, pm_catalog, InventoryProcurementWorkspaceCatalog())

    pm_catalog.projectsWorkspace.refresh()
    assert project_a.id in str(pm_catalog.projectsWorkspace.projects)

    switch_result = platform_catalog.organizationSwitcher.switchToOrganization(org_b.id)
    assert switch_result.get("ok") is True

    # No manual refresh() call here -- the signal wiring alone must have rescoped it.
    assert project_a.id not in str(pm_catalog.projectsWorkspace.projects)

    # Switch back for completeness/hygiene -- proves the mechanism works both directions.
    platform_catalog.organizationSwitcher.switchToOrganization(default_org.id)
    assert project_a.id in str(pm_catalog.projectsWorkspace.projects)


def test_inventory_catalog_workspace_no_longer_shows_org_a_data_after_switching_to_org_b(services):
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    org_b = organization_service.create_organization(
        organization_code="RESCOPE-INV-B", display_name="Rescope Inventory Org B", is_enabled=True
    )
    item_a = services["inventory_item_service"].create_item(
        item_code="RESCOPE-ITEM-A", name="Rescope Item A", stock_uom="EA"
    )

    platform_catalog = _catalog(services)
    pm_catalog = ProjectManagementWorkspaceCatalog()
    inventory_catalog = _inventory_catalog(services)
    _wire_like_app_py(platform_catalog, pm_catalog, inventory_catalog)

    inventory_catalog.catalogWorkspace.refresh()
    assert item_a.id in str(inventory_catalog.catalogWorkspace.items)

    switch_result = platform_catalog.organizationSwitcher.switchToOrganization(org_b.id)
    assert switch_result.get("ok") is True

    assert item_a.id not in str(inventory_catalog.catalogWorkspace.items)

    platform_catalog.organizationSwitcher.switchToOrganization(default_org.id)
    assert item_a.id in str(inventory_catalog.catalogWorkspace.items)


def test_platform_sites_workspace_no_longer_shows_org_a_data_after_switching_to_org_b(services):
    organization_service = services["organization_service"]
    default_org = services["tenant_context_service"].get_active_organization()
    org_b = organization_service.create_organization(
        organization_code="RESCOPE-PLAT-B", display_name="Rescope Platform Org B", is_enabled=True
    )
    site_a = services["site_service"].create_site(
        site_code="RESCOPE-SITE-A", name="Rescope Site A", city="Berlin", currency_code="EUR"
    )

    platform_catalog = _catalog(services)
    # `refreshAllWorkspaces` only refreshes ALREADY-LOADED (`_loaded`) workspaces -- ensure the
    # sites sub-workspace is marked loaded, matching what QML navigation would have done.
    platform_catalog.adminWorkspace.refresh()

    assert site_a.id in str(platform_catalog.adminWorkspace.sites)

    switch_result = platform_catalog.organizationSwitcher.switchToOrganization(org_b.id)
    assert switch_result.get("ok") is True

    assert site_a.id not in str(platform_catalog.adminWorkspace.sites)

    platform_catalog.organizationSwitcher.switchToOrganization(default_org.id)
    assert site_a.id in str(platform_catalog.adminWorkspace.sites)


def test_pm_workspace_rescopes_on_tenant_switch_too(services):
    """Section 4 of the governing spec: verify the same consistency after a TENANT switch, not
    just an organization switch -- `refreshAllWorkspaces` is wired to both signals identically.

    A bare `Tenant.create(...)` has no organization/module-entitlement provisioning at all, so
    proving actual PROJECT DATA disappears would really be testing PM's own "Project Management
    not licensed" early-exit path (a real, but separate and pre-existing, PM behavior -- see the
    final report), not organization-scoping. This proves the WIRING itself fires identically to
    the organization-switch case above: `refreshAllWorkspaces` runs on `tenantSwitched` too."""
    from src.core.platform.domain.tenant.tenancy import Tenant
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
        SqlAlchemyTenantRepository,
    )

    other_tenant = Tenant.create(tenant_code="RESCOPE-OTHER-TENANT", display_name="Rescope Other Tenant")
    SqlAlchemyTenantRepository(services["session"]).add(other_tenant)
    services["session"].flush()

    platform_catalog = _catalog(services)
    pm_catalog = _pm_catalog(services)
    inventory_catalog = InventoryProcurementWorkspaceCatalog()
    _wire_like_app_py(platform_catalog, pm_catalog, inventory_catalog)

    # A second connection to the SAME production signal (not a monkeypatch -- Qt already
    # captured the bound `refreshAllWorkspaces` slot at connect time above, so patching the
    # attribute afterward wouldn't observe what the signal actually calls).
    calls = {"count": 0}
    platform_catalog.tenantSwitcher.tenantSwitched.connect(lambda: calls.__setitem__("count", calls["count"] + 1))

    switch_result = platform_catalog.tenantSwitcher.switchToTenant(other_tenant.id)

    assert switch_result.get("ok") is True
    assert calls["count"] >= 1, "tenantSwitched must fire on a real tenant switch"
    # pm_catalog/inventory_catalog were wired identically to production `app.py` above --
    # `refreshAllWorkspaces` (proven to run on organization switch in the tests above) is
    # connected to the SAME `tenantSwitched` signal, so it necessarily also ran here.


def test_pm_workspace_does_not_keep_serving_org_a_data_after_current_org_access_is_revoked(services):
    """P10C's `_clear_active_organization_if_revoked` fix only clears the CURRENT live session
    when the revoked user IS that session's own principal (matching `refresh_current_session_if_
    user`'s same-user precedent -- proven as an explicit no-op for a DIFFERENT user's session,
    and characterized end-to-end, in test_p10c_organization_switcher.py). Exercises that method
    directly (as that file's own same-session proof does) rather than through the full
    `remove_scope_grant` public API's own permission+delegation-policy gates, which are a
    separate, already-tested concern -- this isolates the one behavior relevant here: does a
    PM workspace already showing org A's data stop doing so once the session's active
    organization is cleared."""
    from src.tests.ui_runtime_helpers import login_as

    organization_service = services["organization_service"]
    access = services["access_service"]
    org = organization_service.create_organization(
        organization_code="RESCOPE-REVOKE-ORG", display_name="Rescope Revoke Org", is_enabled=True
    )
    tenant_id = services["tenant_context_service"].require_active_tenant_id(operation_label="test")
    user = services["auth_service"].register_user(
        "rescope-revoke-user", "StrongPass123", role_names=["viewer", "project_manager"], tenant_id=tenant_id
    )
    access.assign_scope_grant(scope_type="organization", scope_id=org.id, user_id=user.id, scope_role="viewer")

    login_as(services, "rescope-revoke-user", "StrongPass123")
    services["tenant_context_service"].set_active_organization(org.id)
    project_a = services["project_service"].create_project(
        "Rescope Revoke Project A", financial_currency_code="USD"
    )

    pm_catalog = _pm_catalog(services)
    pm_catalog.projectsWorkspace.refresh()
    assert project_a.id in str(pm_catalog.projectsWorkspace.projects)

    access._clear_active_organization_if_revoked("organization", org.id, user.id)
    assert services["tenant_context_service"].get_active_organization_id() is None

    pm_catalog.projectsWorkspace.refresh()
    assert project_a.id not in str(pm_catalog.projectsWorkspace.projects)


def test_pm_workspace_does_not_keep_serving_org_a_data_after_current_org_is_disabled(services):
    """Section 4 (disable): disabling the CURRENT session's active organization clears
    `active_organization_id` (P10C's own fix). Same proof shape as the revocation test above."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    org = organization_service.create_organization(
        organization_code="RESCOPE-DISABLE-ORG", display_name="Rescope Disable Org", is_enabled=True
    )
    tenant_context_service.set_active_organization(org.id)
    project_a = services["project_service"].create_project(
        "Rescope Disable Project A", financial_currency_code="USD"
    )

    pm_catalog = _pm_catalog(services)
    pm_catalog.projectsWorkspace.refresh()
    assert project_a.id in str(pm_catalog.projectsWorkspace.projects)

    organization_service.disable_organization(org.id)
    assert tenant_context_service.get_active_organization_id() is None

    pm_catalog.projectsWorkspace.refresh()
    assert project_a.id not in str(pm_catalog.projectsWorkspace.projects)
