from __future__ import annotations

from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.tests.platform._platform_test_helpers import build_connected_platform_registry


def test_platform_workspace_catalog_exposes_admin_action_lists() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())
    # Access is lazy-loaded now -- construction alone no longer fetches it.
    catalog.adminAccessWorkspace.refresh()

    organizations = catalog.adminWorkspace.organizations
    sites = catalog.adminWorkspace.sites
    departments = catalog.adminWorkspace.departments
    employees = catalog.adminWorkspace.employees
    users = catalog.adminWorkspace.users
    parties = catalog.adminWorkspace.parties
    documents = catalog.adminWorkspace.documents
    selected_document = catalog.adminWorkspace.selectedDocument
    document_preview = catalog.adminWorkspace.documentPreview
    document_links = catalog.adminWorkspace.documentLinks
    document_structures = catalog.adminWorkspace.documentStructures
    access_workspace = catalog.adminAccessWorkspace

    assert organizations["title"] == "Organizations"
    assert organizations["items"][0]["title"] == "TechAsh"
    assert organizations["items"][1]["canSecondaryAction"] is True

    assert sites["title"] == "Sites"
    assert sites["items"][0]["title"] == "Berlin Campus"

    assert departments["title"] == "Departments"
    assert departments["items"][0]["supportingText"] == "Site: Berlin Campus | Location: No default location"

    assert employees["title"] == "Employees"
    assert employees["items"][0]["metaText"].startswith("Full Time")

    assert users["title"] == "Users"
    assert users["items"][0]["supportingText"] == "Admin"

    assert parties["title"] == "Parties"
    assert parties["items"][0]["subtitle"] == "SUP-001 | Supplier"

    assert documents["title"] == "Documents"
    assert documents["items"][0]["supportingText"] == "POL - Policies | Version 1.0 | Current"
    assert selected_document["title"] == "Governance Charter"
    assert selected_document["badges"][2]["value"] == "Local file missing"
    assert document_preview["statusLabel"] == "Local file missing"
    assert document_preview["canOpen"] is False
    assert document_links["title"] == "Linked Records"
    assert len(document_links["items"]) == 2
    assert document_links["items"][0]["statusLabel"] == "Attachment"
    assert document_structures["title"] == "Document Structures"
    assert document_structures["items"][0]["title"] == "Policies"

    assert len(catalog.adminWorkspace.organizationEditorOptions["moduleOptions"]) == 3
    assert len(catalog.adminWorkspace.departmentEditorOptions["siteOptions"]) == 1
    assert len(catalog.adminWorkspace.departmentEditorOptions["locationOptions"]) == 2
    assert len(catalog.adminWorkspace.employeeEditorOptions["departmentOptions"]) == 1
    assert len(catalog.adminWorkspace.userEditorOptions["roleOptions"]) == 2
    assert len(catalog.adminWorkspace.partyEditorOptions["typeOptions"]) >= 3
    assert len(catalog.adminWorkspace.documentEditorOptions["structureOptions"]) == 2
    assert len(catalog.adminWorkspace.documentStructureEditorOptions["parentOptions"]) == 2
    assert len(access_workspace.scopeTypeOptions) == 3
    assert access_workspace.scopeGrants["items"][0]["title"] == "Ada Lovelace"
    assert access_workspace.securityUsers["items"][1]["statusLabel"] == "Locked"


def test_platform_workspace_catalog_runs_admin_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    organization_result = catalog.adminWorkspace.createOrganization(
        {
            "organizationCode": "QML",
            "displayName": "QML Labs",
            "timezoneName": "Europe/Berlin",
            "baseCurrency": "EUR",
            "isEnabled": False,
            "initialModuleCodes": ["project_management"],
        }
    )
    activate_result = catalog.adminWorkspace.enableOrganization("org-2")
    site_result = catalog.adminWorkspace.createSite(
        {
            "siteCode": "HAM",
            "name": "Hamburg Hub",
            "description": "Logistics hub",
            "city": "Hamburg",
            "country": "DE",
            "timezoneName": "Europe/Berlin",
            "currencyCode": "EUR",
            "siteType": "office",
            "status": "active",
            "notes": "",
            "isActive": True,
        }
    )
    department_result = catalog.adminWorkspace.toggleDepartmentActive("dep-2")
    employee_result = catalog.adminWorkspace.createEmployee(
        {
            "employeeCode": "E-003",
            "fullName": "Katherine Johnson",
            "departmentId": "dep-1",
            "departmentName": "Engineering",
            "siteId": "site-1",
            "siteName": "Berlin Campus",
            "title": "Analyst",
            "employmentType": "FULL_TIME",
            "email": "katherine@example.com",
            "phone": "555-0100",
            "isActive": True,
        }
    )
    user_result = catalog.adminWorkspace.createUser(
        {
            "username": "katherine",
            "displayName": "Katherine Johnson",
            "email": "katherine@example.com",
            "password": "secret",
            "roleNames": ["admin"],
            "isActive": True,
        }
    )
    party_result = catalog.adminWorkspace.createParty(
        {
            "partyCode": "VEN-100",
            "partyName": "Orbit Supply",
            "partyType": "VENDOR",
            "contactName": "Helen Morris",
            "email": "orbit@example.com",
            "country": "DE",
            "city": "Munich",
            "isActive": True,
        }
    )
    document_result = catalog.adminWorkspace.createDocument(
        {
            "documentCode": "DOC-003",
            "title": "Safety Policy",
            "documentType": "POLICY",
            "documentStructureId": "structure-1",
            "storageKind": "FILE_PATH",
            "storageUri": "/docs/doc-3.pdf",
            "fileName": "doc-3.pdf",
            "mimeType": "application/pdf",
            "sourceSystem": "desktop",
            "confidentialityLevel": "internal",
            "businessVersionLabel": "2.0",
            "isCurrent": True,
            "isActive": True,
        }
    )

    assert organization_result == {"ok": True, "category": "", "code": "", "message": "Organization created."}
    assert activate_result == {"ok": True, "category": "", "code": "", "message": "Organization enabled."}
    assert site_result == {"ok": True, "category": "", "code": "", "message": "Site created."}
    assert department_result == {"ok": True, "category": "", "code": "", "message": "Department active state updated."}
    assert employee_result == {"ok": True, "category": "", "code": "", "message": "Employee created."}
    assert user_result == {"ok": True, "category": "", "code": "", "message": "User created."}
    assert party_result == {"ok": True, "category": "", "code": "", "message": "Party created."}
    assert document_result == {"ok": True, "category": "", "code": "", "message": "Document created."}

    organization_titles = [item["title"] for item in catalog.adminWorkspace.organizations["items"]]
    site_titles = [item["title"] for item in catalog.adminWorkspace.sites["items"]]
    employee_titles = [item["title"] for item in catalog.adminWorkspace.employees["items"]]
    user_titles = [item["title"] for item in catalog.adminWorkspace.users["items"]]
    party_titles = [item["title"] for item in catalog.adminWorkspace.parties["items"]]
    document_titles = [item["title"] for item in catalog.adminWorkspace.documents["items"]]
    department_by_id = {item["id"]: item for item in catalog.adminWorkspace.departments["items"]}

    assert "QML Labs" in organization_titles
    assert catalog.adminWorkspace.organizations["items"][1]["statusLabel"] == "Enabled"
    assert "Hamburg Hub" in site_titles
    assert catalog.adminWorkspace.sites["items"][-1]["organizationName"] == "Operations"
    assert department_by_id["dep-2"]["statusLabel"] == "Active"
    assert "Katherine Johnson" in employee_titles
    assert "Katherine Johnson" in user_titles
    created_user = next(
        item
        for item in catalog.adminWorkspace.users["items"]
        if item["title"] == "Katherine Johnson"
    )
    assert created_user["supportingText"] == "Viewer"
    assert "Orbit Supply" in party_titles
    assert "Safety Policy" in document_titles
    assert catalog.adminWorkspace.feedbackMessage == "Document created."


def test_platform_workspace_catalog_updates_extended_admin_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    update_user_result = catalog.adminWorkspace.updateUser(
        {
            "userId": "user-2",
            "username": "grace",
            "displayName": "Grace Hopper",
            "email": "grace@example.com",
            "password": "updated-secret",
            "roleNames": ["planner"],
            "currentRoleNames": ["viewer"],
            "isActive": True,
            "currentIsActive": False,
        }
    )
    toggle_party_result = catalog.adminWorkspace.togglePartyActive("party-2")
    toggle_document_result = catalog.adminWorkspace.toggleDocumentActive("doc-2")

    assert update_user_result == {"ok": True, "category": "", "code": "", "message": "User updated."}
    assert toggle_party_result == {"ok": True, "category": "", "code": "", "message": "Party active state updated."}
    assert toggle_document_result == {"ok": True, "category": "", "code": "", "message": "Document active state updated."}

    user_by_id = {item["id"]: item for item in catalog.adminWorkspace.users["items"]}
    party_by_id = {item["id"]: item for item in catalog.adminWorkspace.parties["items"]}
    document_by_id = {item["id"]: item for item in catalog.adminWorkspace.documents["items"]}

    assert user_by_id["user-2"]["statusLabel"] == "Locked"
    assert user_by_id["user-2"]["state"]["isActive"] is True
    assert user_by_id["user-2"]["supportingText"] == "Planner"
    assert party_by_id["party-2"]["statusLabel"] == "Active"
    assert document_by_id["doc-2"]["state"]["isActive"] is False
    assert catalog.adminWorkspace.feedbackMessage == "Document active state updated."


def test_platform_workspace_catalog_can_switch_document_focus() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    catalog.adminWorkspace.selectDocument("doc-2")

    assert catalog.adminWorkspace.selectedDocument["title"] == "Archived Procedure"
    assert catalog.adminWorkspace.selectedDocument["summary"].endswith("0 linked records")
    assert catalog.adminWorkspace.documentLinks["items"] == []
    assert catalog.adminWorkspace.documentLinks["emptyState"] == "No linked records yet."
    assert catalog.adminWorkspace.documentPreview["statusLabel"] == "Local file missing"


def test_platform_workspace_catalog_runs_document_management_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    create_structure_result = catalog.adminWorkspace.createDocumentStructure(
        {
            "structureCode": "CERT",
            "name": "Certificates",
            "description": "Compliance certificates",
            "parentStructureId": "",
            "objectScope": "GENERAL",
            "defaultDocumentType": "CERTIFICATE",
            "sortOrder": 3,
            "notes": "",
            "isActive": True,
        }
    )
    update_structure_result = catalog.adminWorkspace.updateDocumentStructure(
        {
            "structureId": "structure-2",
            "expectedVersion": 1,
            "structureCode": "PROC",
            "name": "Operating Procedures",
            "description": "Procedure documents",
            "parentStructureId": "",
            "objectScope": "GENERAL",
            "defaultDocumentType": "PROCEDURE",
            "sortOrder": 2,
            "notes": "",
            "isActive": True,
        }
    )
    toggle_structure_result = catalog.adminWorkspace.toggleDocumentStructureActive("structure-2")
    catalog.adminWorkspace.selectDocument("doc-2")
    add_link_result = catalog.adminWorkspace.addDocumentLink(
        {
            "documentId": "doc-2",
            "moduleCode": "inventory_procurement",
            "entityType": "item",
            "entityId": "item-9",
            "linkRole": "reference",
        }
    )
    remove_link_result = catalog.adminWorkspace.removeDocumentLink(
        catalog.adminWorkspace.documentLinks["items"][0]["id"]
    )

    assert create_structure_result == {"ok": True, "category": "", "code": "", "message": "Document structure created."}
    assert update_structure_result == {"ok": True, "category": "", "code": "", "message": "Document structure updated."}
    assert toggle_structure_result == {"ok": True, "category": "", "code": "", "message": "Document structure active state updated."}
    assert add_link_result == {"ok": True, "category": "", "code": "", "message": "Document link added."}
    assert remove_link_result == {"ok": True, "category": "", "code": "", "message": "Document link removed."}

    structure_titles = [item["title"] for item in catalog.adminWorkspace.documentStructures["items"]]
    structure_by_id = {item["id"]: item for item in catalog.adminWorkspace.documentStructures["items"]}

    assert "Certificates" in structure_titles
    assert structure_by_id["structure-2"]["title"] == "Operating Procedures"
    assert structure_by_id["structure-2"]["statusLabel"] == "Inactive"
    assert catalog.adminWorkspace.documentLinks["items"] == []
    assert catalog.adminWorkspace.feedbackMessage == "Document link removed."
