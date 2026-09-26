"""Organization Detail's Sites/Departments/Employees/Documents row
activation navigates to that entity's own standalone workspace detail page
(relatedRecordRequested) instead of nesting a second copy of that detail UI
inline -- nesting duplicated state across two owners and was the root cause
of a real cross-scope InlineMessage leak (a stale list-scoped message could
show up as if it belonged to whatever record's nested detail had just been
opened). Removing the nested detail view removes that leak vector entirely;
these tests verify row activation emits the correct cross-workspace
navigation request rather than any local nested-detail state."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QCoreApplication, QMetaObject, qInstallMessageHandler

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


def _pump(n: int = 10) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def _load_detail_page(services, qapp, *, org_code: str, org_name: str):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    catalog, admin = _build_admin_workspace(services)

    org = organization_service.create_organization(
        organization_code=org_code, display_name=org_name, timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)

    engine = create_qml_engine()
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
    return engine, root, admin, catalog


def test_site_row_activation_emits_related_record_request_not_local_nested_state(services, qapp) -> None:
    site = services["site_service"].create_site(site_code="NAV-SITE-1", name="Nav Site One", city="Lagos", country="Nigeria")

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine, root, admin, _catalog = _load_detail_page(services, qapp, org_code="NAV-ORG-1", org_name="Nav Org One")
    try:
        _pump()
        requests: list[tuple[str, str]] = []
        root.relatedRecordRequested.connect(lambda destination_id, row_id: requests.append((destination_id, row_id)))

        assert _invoke(root, "_openSiteDetail", site.id)
        _pump()

        assert requests == [("sites", site.id)]
        # No local nested-detail property survives on this page anymore --
        # the section itself no longer even exposes one.
        assert root.property("_sitesDetailOpen") is None

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


def test_department_row_activation_emits_related_record_request(services, qapp) -> None:
    department = services["department_service"].create_department(department_code="NAV-DEPT-1", name="Nav Department One")

    engine, root, admin, _catalog = _load_detail_page(services, qapp, org_code="NAV-ORG-2", org_name="Nav Org Two")
    try:
        _pump()
        requests: list[tuple[str, str]] = []
        root.relatedRecordRequested.connect(lambda destination_id, row_id: requests.append((destination_id, row_id)))

        assert _invoke(root, "_openDepartmentDetail", department.id)
        _pump()

        assert requests == [("departments", department.id)]
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()


def test_employee_row_activation_emits_related_record_request(services, qapp) -> None:
    employee = services["employee_service"].create_employee(employee_code="NAV-EMP-1", full_name="Nav Employee One")

    engine, root, admin, _catalog = _load_detail_page(services, qapp, org_code="NAV-ORG-3", org_name="Nav Org Three")
    try:
        _pump()
        requests: list[tuple[str, str]] = []
        root.relatedRecordRequested.connect(lambda destination_id, row_id: requests.append((destination_id, row_id)))

        assert _invoke(root, "_openEmployeeDetail", employee.id)
        _pump()

        assert requests == [("employees", employee.id)]
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()


def test_document_row_activation_emits_related_record_request(services, qapp) -> None:
    # selectDocument()/inspectDocument() resolve the ACTIVE organization
    # internally, so the document must be created after _load_detail_page
    # activates its organization -- matching OrganizationDocumentsSection's
    # own documented isViewingActiveOrganization caveat.
    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine, root, admin, _catalog = _load_detail_page(services, qapp, org_code="NAV-ORG-4", org_name="Nav Org Four")
    document = services["document_service"].create_document(
        document_code="NAV-DOC-1", title="Nav Document One", storage_uri="C:/docs/nav.pdf"
    )
    try:
        _pump()
        requests: list[tuple[str, str]] = []
        root.relatedRecordRequested.connect(lambda destination_id, row_id: requests.append((destination_id, row_id)))

        assert _invoke(root, "_openDocumentDetail", document.id)
        _pump()

        assert requests == [("documents", document.id)]

        relevant = [
            m for m in messages
            if "TypeError" in m or "ReferenceError" in m or "is not defined" in m
            or "unknown icon name" in m or "Cannot read propert" in m
        ]
        assert relevant == [], relevant
    finally:
        qInstallMessageHandler(previous_handler)
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()


def test_activity_row_activation_routes_through_the_same_related_record_request(services, qapp) -> None:
    """An Activity entry referencing a site now navigates the same way a
    Sites-tab row activation does -- no more local tab-switching, since
    there is no longer a local nested detail to switch to."""
    site = services["site_service"].create_site(site_code="NAV-SITE-2", name="Nav Site Two", city="Lagos", country="Nigeria")

    engine, root, admin, _catalog = _load_detail_page(services, qapp, org_code="NAV-ORG-5", org_name="Nav Org Five")
    try:
        _pump()
        requests: list[tuple[str, str]] = []
        root.relatedRecordRequested.connect(lambda destination_id, row_id: requests.append((destination_id, row_id)))

        ok = QMetaObject.invokeMethod(
            root, "_openEntityFromActivity", Q_ARG("QVariant", "site"), Q_ARG("QVariant", site.id)
        )
        assert ok
        _pump()

        assert requests == [("sites", site.id)]
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
