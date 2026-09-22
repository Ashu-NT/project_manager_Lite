"""Phase K, Sites vertical slice: real end-to-end QML load of
AdminOrganizationDetailPage.qml's Sites tab against a fully-wired
PlatformWorkspaceCatalog -- proves the tenant-scoped, paginated
organizationSitesPage() call is wired correctly end-to-end (not just at the
Python layer), including while viewing a NON-active organization."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, qInstallMessageHandler

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

DETAIL_PAGE = Path(
    "src/ui_qml/platform/qml/workspaces/organizations/AdminOrganizationDetailPage.qml"
)


def _build_admin_workspace(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    return catalog, catalog.adminWorkspace


def _create_org(services, code: str, name: str) -> str:
    organization = services["organization_service"].create_organization(
        organization_code=code, display_name=name, timezone_name="UTC", base_currency="USD"
    )
    return organization.id


def _load_detail_page(engine, organization: dict, workspace_controller, platform_catalog):
    load_qml(
        engine,
        DETAIL_PAGE.resolve(),
        initial_properties={
            "organization": organization,
            "workspaceController": workspace_controller,
            "platformCatalog": platform_catalog,
        },
    )
    return engine.rootObjects()[0]


def test_sites_tab_loads_real_paginated_data_for_a_non_active_organization(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    catalog, admin = _build_admin_workspace(services)

    org_a = organization_service.create_organization(
        organization_code="QML-SITE-A", display_name="QML Site Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    site_service = services["site_service"]
    site_service.create_site(site_code="QSITE-1", name="Alpha Site", city="Lagos", country="Nigeria")
    site_service.create_site(site_code="QSITE-2", name="Beta Site", city="Abuja", country="Nigeria")

    org_b = organization_service.create_organization(
        organization_code="QML-SITE-B", display_name="QML Site Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)  # active org is now B, not A

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        organization_payload = {
            "id": org_a.id,
            "title": org_a.display_name,
            "statusLabel": {"label": "Active", "tone": "success"},
            "subtitle": f"{org_a.organization_code} | UTC",
            "state": {
                "organizationId": org_a.id,
                "organizationCode": org_a.organization_code,
                "status": "active",
            },
        }
        root = _load_detail_page(engine, organization_payload, admin, catalog)
        for _ in range(20):
            QCoreApplication.processEvents()

        # Component.onCompleted already fetched page 1 -- but confirm the
        # explicit section switch path also works (mirrors real navigation).
        root.setProperty("activeSectionIndex", 1)
        for _ in range(20):
            QCoreApplication.processEvents()

        sites_catalog = root.property("_sitesCatalog")
        sites_catalog = sites_catalog.toVariant() if hasattr(sites_catalog, "toVariant") else sites_catalog
        names = sorted(item["title"] for item in sites_catalog["items"])
        assert names == ["Alpha Site", "Beta Site"], sites_catalog

        # Every returned row genuinely belongs to org A, not the active org B.
        for item in sites_catalog["items"]:
            assert item["state"]["organizationId"] == org_a.id

        assert sites_catalog["paginated"] is True
        assert sites_catalog["totalCount"] == 2

        # Not viewing your own active organization -- create must be gated off.
        assert root.property("_canCreateSite") is False

        relevant = [
            m for m in messages
            if "TypeError" in m or "ReferenceError" in m or "is not defined" in m
            or "unknown icon name" in m or "Cannot read propert" in m
        ]
        assert relevant == [], relevant
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qInstallMessageHandler(previous_handler)


def test_sites_tab_controller_slot_applies_status_filter_server_side(services, qapp) -> None:
    """Same `organizationSitesPage` controller slot the Sites tab's status
    ComboBox calls on `onActivated` -- exercised directly here (rather than
    synthesizing a ComboBox interaction) to prove the filter argument
    actually reaches the tenant-scoped service call through the full
    Controller -> Presenter -> Desktop API -> Service chain."""
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    _catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="QML-FILTER", display_name="QML Filter Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site_service = services["site_service"]
    site_service.create_site(site_code="FIL-ACT", name="Filter Active Site")
    inactive = site_service.create_site(site_code="FIL-INA", name="Filter Inactive Site")
    site_service.update_site(inactive.id, is_active=False)

    result = admin.organizationSitesPage(org.id, 1, 25, "", "active")
    names = [item["title"] for item in result["items"]]
    assert names == ["Filter Active Site"]

    result = admin.organizationSitesPage(org.id, 1, 25, "", "inactive")
    names = [item["title"] for item in result["items"]]
    assert names == ["Filter Inactive Site"]

    result = admin.organizationSitesPage(org.id, 1, 25, "Beta-does-not-exist", "")
    assert result["items"] == []
    assert result["totalCount"] == 2
    assert result["filteredTotal"] == 0
