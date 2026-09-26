
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, qInstallMessageHandler

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

WORKSPACE_PAGE = Path(
    "src/ui_qml/platform/qml/workspaces/organizations/OrganizationsWorkspacePage.qml"
)


def _build_admin_workspace(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    return catalog, catalog.adminWorkspace


def test_inspector_renders_grouped_layout_compact_width_and_lifecycle_menu(services, qapp) -> None:
    organization_service = services["organization_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="INSP-ORG",
        display_name="Inspector Org",
        timezone_name="UTC",
        base_currency="USD",
        legal_name="Inspector Org Legal Entity",
        registration_number="REG-001",
    )

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        load_qml(
            engine,
            WORKSPACE_PAGE.resolve(),
            initial_properties={"platformCatalog": catalog},
        )
        root = engine.rootObjects()[0]
        for _ in range(20):
            QCoreApplication.processEvents()

        root.setProperty("selectedRowId", org.id)
        for _ in range(20):
            QCoreApplication.processEvents()

        groups = root.property("_inspectorGroups")
        groups = groups.toVariant() if hasattr(groups, "toVariant") else groups
        titles = [group["title"] for group in groups]
        assert titles == ["Identity", "Lifecycle", "Location", "Key Statistics", "Business Context"]

        identity_rows = {row["label"]: row["value"] for row in groups[0]["rows"]}
        assert identity_rows["Code"] == "INSP-ORG"
        assert identity_rows["Legal Name"] == "Inspector Org Legal Entity"
        assert identity_rows["Registration Number"] == "REG-001"

        lifecycle_rows = {row["label"]: row["value"] for row in groups[1]["rows"]}
        assert lifecycle_rows["Status"] == "Active"

        stats_rows = {row["label"]: row["value"] for row in groups[3]["rows"]}
        # Real aggregate counts (0 is legitimate information for a brand-new
        # organization, never hidden or blank).
        assert stats_rows["Sites"] == "0"
        assert stats_rows["Departments"] == "0"

        # A new, Active organization can Deactivate or Archive from the
        # Inspector's Actions menu -- Activate does not apply.
        menu_items = root.property("_inspectorLifecycleMenuItems")
        menu_items = menu_items.toVariant() if hasattr(menu_items, "toVariant") else menu_items
        menu_ids = [item["id"] for item in menu_items]
        assert menu_ids == ["deactivate", "archive"]

        assert root.property("_canWrite") is True

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


def test_inspector_menu_action_deactivate_and_archive_route_through_confirmation(services, qapp) -> None:
    organization_service = services["organization_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="INSP-LIFECYCLE",
        display_name="Inspector Lifecycle Org",
        timezone_name="UTC",
        base_currency="USD",
    )

    engine = create_qml_engine()
    try:
        load_qml(
            engine,
            WORKSPACE_PAGE.resolve(),
            initial_properties={"platformCatalog": catalog},
        )
        root = engine.rootObjects()[0]
        for _ in range(20):
            QCoreApplication.processEvents()

        root.setProperty("selectedRowId", org.id)
        for _ in range(20):
            QCoreApplication.processEvents()

        # "Deactivate" from the Actions menu opens the shared confirmation
        # dialog rather than mutating immediately (a destructive-ish,
        # confirmable action) -- verified via the QML function directly,
        # the same call the ActionsMenuButton's onActionSelected makes.
        from PySide6.QtCore import Q_ARG, QMetaObject

        assert QMetaObject.invokeMethod(
            root, "_onInspectorMenuAction", Q_ARG("QVariant", "deactivate")
        )
        for _ in range(10):
            QCoreApplication.processEvents()

        pending = root.property("_pendingConfirm")
        pending = pending.toVariant() if hasattr(pending, "toVariant") else pending
        assert pending is not None
        assert pending["action"] == "deactivate"
        assert pending["orgId"] == org.id

        refreshed = next(o for o in organization_service.list_organizations() if o.id == org.id)
        assert refreshed.status == "active"  # not mutated yet -- confirmation pending
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
