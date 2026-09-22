"""Regression coverage for a reported InlineMessage leakage bug: Organization
Detail forwards its own errorMessage/feedbackMessage into both a section's
list view AND that section's nested entity detail view (see
OrganizationSitesSection.qml and its Departments/Employees/Documents
siblings). Since both consume the SAME shared controller-level string,
opening or closing a nested entity's detail without clearing it lets a
stale list-scoped message leak in and display as if it were about the
specific record just opened (or the reverse, on the way back to the list).
_openXDetail()/_closeXDetail() in AdminOrganizationDetailPage.qml now call
workspaceController.clearMessages() at each of those transitions."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, Q_ARG, QMetaObject, qInstallMessageHandler

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


def _invoke(root, method_name: str, arg: str) -> bool:
    return QMetaObject.invokeMethod(root, method_name, Q_ARG("QVariant", arg))


def _invoke_no_args(root, method_name: str) -> bool:
    return QMetaObject.invokeMethod(root, method_name)


def _pump(n: int = 10) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def test_opening_and_closing_nested_site_detail_clears_stale_shared_message(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="LEAK-ORG-1", display_name="Leak Org One", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    site = services["site_service"].create_site(site_code="LEAK-SITE-1", name="Leak Site One", city="Lagos", country="Nigeria")

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        organization_payload = {
            "id": org.id,
            "title": org.display_name,
            "statusLabel": {"label": "Active", "tone": "success"},
            "subtitle": f"{org.organization_code} | UTC",
            "state": {"organizationId": org.id, "organizationCode": org.organization_code, "status": "active"},
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
        _pump()

        # Simulate a stale list-scoped message still sitting on the shared
        # controller (e.g. a prior failed Sites-list action).
        admin._set_error_message("Stale list-level error")
        assert admin.errorMessage == "Stale list-level error"

        assert _invoke(root, "_openSiteDetail", site.id)
        _pump()
        assert admin.errorMessage == "", (
            "opening the nested Site detail must not carry a stale "
            "list-scoped message in as if it belonged to this site"
        )

        admin._set_feedback_message("Stale detail-level success")
        assert _invoke_no_args(root, "_closeSiteDetail")
        _pump()
        assert admin.feedbackMessage == "", (
            "closing the nested Site detail back to the list must not "
            "carry its stale message back onto the list"
        )

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


def test_opening_and_closing_nested_document_detail_clears_stale_shared_message(services, qapp) -> None:
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code="LEAK-ORG-2", display_name="Leak Org Two", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    document = services["document_service"].create_document(
        document_code="LEAK-DOC-1", title="Leak Document One", storage_uri="C:/docs/leak.pdf"
    )

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        organization_payload = {
            "id": org.id,
            "title": org.display_name,
            "statusLabel": {"label": "Active", "tone": "success"},
            "subtitle": f"{org.organization_code} | UTC",
            "state": {"organizationId": org.id, "organizationCode": org.organization_code, "status": "active"},
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
        _pump()

        admin._set_error_message("Stale documents-list error")
        assert _invoke(root, "_openDocumentDetail", document.id)
        _pump()
        assert admin.errorMessage == ""

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
