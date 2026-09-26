"""Platform > Sites' primary workspace list is now server-side paginated,
scoped to the caller's active organization -- the ambient-context
counterpart to Organization Detail's own explicit-organization_id Sites
tab (already covered by test_organization_detail_sites_tab.py), reusing
the exact same list_sites_page_for_organization backend call."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_sites_workspace_list_is_paginated_and_scoped_to_active_organization(services):
    site_service = services["site_service"]
    tenant_context_service = services["tenant_context_service"]
    active_org = tenant_context_service.get_active_organization()

    for i in range(3):
        site_service.create_site(site_code=f"PAGN-A-{i}", name=f"Active Org Site {i}")

    other_org = services["organization_service"].create_organization(
        organization_code="PAGN-OTHER", display_name="Other Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_org.id)
    site_service.create_site(site_code="PAGN-B-0", name="Other Org Site")
    tenant_context_service.set_active_organization(active_org.id)

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    admin.refresh()
    result = admin.sites

    assert result["paginated"] is True
    assert result["page"] == 1
    assert result["pageSize"] == 25
    site_names = {item["title"] for item in result["items"]}
    assert {"Active Org Site 0", "Active Org Site 1", "Active Org Site 2"} <= site_names
    assert "Other Org Site" not in site_names


def test_sites_workspace_search_and_page_size_round_trip_through_admin_workspace(services):
    site_service = services["site_service"]
    for i in range(3):
        site_service.create_site(site_code=f"PAGN-C-{i}", name=f"Findme Site {i}")
    site_service.create_site(site_code="PAGN-D-0", name="Unrelated Site")

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    admin.setSiteSearchText("Findme")
    result = admin.sites
    site_names = {item["title"] for item in result["items"]}
    assert site_names == {"Findme Site 0", "Findme Site 1", "Findme Site 2"}
    assert "Unrelated Site" not in site_names

    admin.setSiteSearchText("")
    admin.setSitePageSize(50)
    assert admin.sites["pageSize"] == 50
