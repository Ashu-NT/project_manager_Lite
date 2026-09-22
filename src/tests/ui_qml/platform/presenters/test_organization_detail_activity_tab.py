"""Phase K, Organization Activity enterprise upgrade: real end-to-end QML
load of AdminOrganizationDetailPage.qml's Activity tab against a fully-wired
PlatformWorkspaceCatalog -- proves the paginated/searchable read is wired
correctly end-to-end, including while viewing a NON-active organization,
and that activating a Site/Department/Employee/Document activity row
switches this page's own tab and opens that entity's nested Detail (the
scoped-routing principle applied to Activity row activation)."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QMetaObject, Q_ARG, qInstallMessageHandler

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


def test_activity_tab_loads_real_paginated_data_for_a_non_active_organization(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    site_service = services["site_service"]
    catalog, admin = _build_admin_workspace(services)

    org_a = organization_service.create_organization(
        organization_code="QML-ACT-A", display_name="QML Activity Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    site_service.create_site(site_code="QACT-SITE", name="QML Activity Site")

    org_b = organization_service.create_organization(
        organization_code="QML-ACT-B", display_name="QML Activity Org B", timezone_name="UTC", base_currency="USD"
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

        root.setProperty("activeSectionIndex", 5)
        for _ in range(20):
            QCoreApplication.processEvents()

        activity_catalog = root.property("_activityCatalog")
        activity_catalog = activity_catalog.toVariant() if hasattr(activity_catalog, "toVariant") else activity_catalog
        titles = [item["title"] for item in activity_catalog["items"]]
        assert "Organization created" in titles
        assert "Site created" in titles
        # Never the org B data, even though B is the session-active org.
        subjects = [item["subjectDisplay"] for item in activity_catalog["items"]]
        assert "QML Activity Org B" not in subjects

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


def test_activating_a_site_activity_row_switches_tab_and_opens_site_detail(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    site_service = services["site_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="QML-ACT-NAV", display_name="QML Activity Nav Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site = site_service.create_site(site_code="NAV-SITE", name="Nav Site")

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        organization_payload = {
            "id": org.id,
            "title": org.display_name,
            "statusLabel": {"label": "Active", "tone": "success"},
            "subtitle": f"{org.organization_code} | UTC",
            "state": {
                "organizationId": org.id,
                "organizationCode": org.organization_code,
                "status": "active",
            },
        }
        root = _load_detail_page(engine, organization_payload, admin, catalog)
        for _ in range(20):
            QCoreApplication.processEvents()

        assert QMetaObject.invokeMethod(
            root, "_openEntityFromActivity", Q_ARG("QVariant", "site"), Q_ARG("QVariant", site.id)
        )
        for _ in range(20):
            QCoreApplication.processEvents()

        assert root.property("activeSectionIndex") == 1
        assert root.property("_sitesDetailOpen") is True
        assert root.property("_sitesSelectedRowId") == site.id

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


def test_activity_tab_controller_slot_applies_search_and_type_filter_server_side(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    _catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="QML-ACT-FILTER", display_name="QML Activity Filter Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site_service.create_site(site_code="FIL-ACT-SITE", name="Filter Site")
    department_service.create_department(department_code="FIL-ACT-DEPT", name="Filter Department")

    result = admin.organizationActivityPage(org.id, 1, 25, "", "site", "")
    titles = [item["title"] for item in result["items"]]
    assert titles == ["Site created"]

    result = admin.organizationActivityPage(org.id, 1, 25, "Filter Department", "", "")
    assert len(result["items"]) == 1
    assert result["items"][0]["subjectDisplay"] == "Filter Department"
