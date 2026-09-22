
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


def test_related_actions_and_key_statistics_switch_the_local_tab_not_global_navigation(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="ROUTE-ORG", display_name="Routing Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)

    bubbled_destinations: list[str] = []
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
        load_qml(
            engine,
            DETAIL_PAGE.resolve(),
            initial_properties={
                "organization": organization_payload,
                "workspaceController": admin,
                "platformCatalog": catalog,
            },
        )
        root = engine.rootObjects()[0]
        root.navigateToDestination.connect(lambda destination_id: bubbled_destinations.append(destination_id))
        for _ in range(20):
            QCoreApplication.processEvents()

        assert root.property("activeSectionIndex") == 0  # Overview, the default landing tab

        # Sites, via the same routing function Key Statistics/Related
        # Actions call -- must switch this page's own tab...
        assert QMetaObject_invoke(root, "_navigateFromOverview", "sites")
        for _ in range(10):
            QCoreApplication.processEvents()
        assert root.property("activeSectionIndex") == 1
        # ...not bubble up to the global Platform workspace switch.
        assert bubbled_destinations == []

        assert QMetaObject_invoke(root, "_navigateFromOverview", "departments")
        for _ in range(10):
            QCoreApplication.processEvents()
        assert root.property("activeSectionIndex") == 2
        assert bubbled_destinations == []

        assert QMetaObject_invoke(root, "_navigateFromOverview", "employees")
        for _ in range(10):
            QCoreApplication.processEvents()
        assert root.property("activeSectionIndex") == 3
        assert bubbled_destinations == []

        assert QMetaObject_invoke(root, "_navigateFromOverview", "documents")
        for _ in range(10):
            QCoreApplication.processEvents()
        assert root.property("activeSectionIndex") == 4
        assert bubbled_destinations == []

        # An id with no local tab of its own still bubbles up as before --
        # the fix scopes known child-entity ids, it doesn't disable
        # cross-workspace navigation entirely.
        assert QMetaObject_invoke(root, "_navigateFromOverview", "control_audit")
        for _ in range(10):
            QCoreApplication.processEvents()
        assert bubbled_destinations == ["control_audit"]

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


def QMetaObject_invoke(root, method_name: str, arg: str) -> bool:
    from PySide6.QtCore import QMetaObject, Q_ARG

    return QMetaObject.invokeMethod(root, method_name, Q_ARG("QVariant", arg))
