from __future__ import annotations

from src.api.desktop.platform import (
    DocumentCreateCommand,
    DocumentLinkCreateCommand,
    DocumentStructureCreateCommand,
    DocumentStructureUpdateCommand,
    PartyCreateCommand,
    PartyUpdateCommand,
    PlatformDocumentDesktopApi,
    PlatformPartyDesktopApi,
    PlatformUserDesktopApi,
    UserCreateCommand,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.api.desktop.runtime import build_desktop_api_registry


def _document_api(services) -> PlatformDocumentDesktopApi:
    return PlatformDocumentDesktopApi(document_service=services["document_service"])


def _party_api(services) -> PlatformPartyDesktopApi:
    return PlatformPartyDesktopApi(party_service=services["party_service"])


def _user_api(services) -> PlatformUserDesktopApi:
    return PlatformUserDesktopApi(auth_service=services["auth_service"])


def test_platform_party_desktop_api_manages_party_dtos(services):
    api = _party_api(services)

    context_result = api.get_context()
    create_result = api.create_party(
        PartyCreateCommand(
            party_code="SUP-001",
            party_name="North Supply",
            party_type="SUPPLIER",
            country="Germany",
            city="Berlin",
        )
    )

    assert context_result.ok is True
    assert context_result.data is not None
    assert context_result.data.display_name == "Default Organization"
    assert create_result.ok is True
    assert create_result.data is not None
    assert create_result.data.party_type.value == "SUPPLIER"

    update_result = api.update_party(
        PartyUpdateCommand(
            party_id=create_result.data.id,
            party_name="North Supply GmbH",
            is_active=False,
            expected_version=create_result.data.version,
        )
    )

    assert update_result.ok is True
    assert update_result.data is not None
    assert update_result.data.party_name == "North Supply GmbH"
    assert update_result.data.is_active is False


def test_platform_document_desktop_api_manages_document_dtos_and_links(services):
    api = _document_api(services)

    structure_result = api.create_document_structure(
        DocumentStructureCreateCommand(
            structure_code="PM_DOCS",
            name="Project Documents",
            object_scope="PROJECT",
            default_document_type="GENERAL",
        )
    )

    assert structure_result.ok is True
    assert structure_result.data is not None

    document_result = api.create_document(
        DocumentCreateCommand(
            document_code="DOC-001",
            title="Execution Plan",
            document_type="GENERAL",
            document_structure_id=structure_result.data.id,
            storage_kind="REFERENCE",
            storage_uri="vault://pm/execution-plan",
            business_version_label="Rev A",
        )
    )

    assert document_result.ok is True
    assert document_result.data is not None
    assert document_result.data.document_structure_id == structure_result.data.id

    link_result = api.add_link(
        DocumentLinkCreateCommand(
            document_id=document_result.data.id,
            module_code="project_management",
            entity_type="project",
            entity_id="project-1",
            link_role="reference",
        )
    )
    update_structure_result = api.update_document_structure(
        DocumentStructureUpdateCommand(
            structure_id=structure_result.data.id,
            name="Project Controls Documents",
            expected_version=structure_result.data.version,
        )
    )
    list_links_result = api.list_links(document_result.data.id)

    assert link_result.ok is True
    assert link_result.data is not None
    assert update_structure_result.ok is True
    assert update_structure_result.data is not None
    assert update_structure_result.data.name == "Project Controls Documents"
    assert list_links_result.ok is True
    assert list_links_result.data is not None
    assert [row.module_code for row in list_links_result.data] == ["project_management"]


def test_platform_user_desktop_api_manages_user_dtos_and_roles(services):
    api = _user_api(services)

    create_result = api.create_user(
        UserCreateCommand(
            username="desktop-user",
            password="StrongPass123",
            display_name="Desktop User",
            email="desktop@example.com",
            role_names=("viewer",),
        )
    )

    assert create_result.ok is True
    assert create_result.data is not None
    assert create_result.data.role_names == ("viewer",)

    assign_result = api.assign_role(create_result.data.id, "planner")
    update_result = api.update_user(
        UserUpdateCommand(
            user_id=create_result.data.id,
            display_name="Desktop Planner",
            email="planner@example.com",
        )
    )
    reset_result = api.reset_password(
        UserPasswordResetCommand(
            user_id=create_result.data.id,
            new_password="EvenStronger123",
        )
    )

    assert assign_result.ok is True
    assert assign_result.data is not None
    assert "planner" in assign_result.data.role_names
    assert update_result.ok is True
    assert update_result.data is not None
    assert update_result.data.display_name == "Desktop Planner"
    assert reset_result.ok is True
    assert reset_result.data is not None
    assert reset_result.data.must_change_password is True


def test_build_desktop_api_registry_exposes_platform_admin_adapters(services):
    registry = build_desktop_api_registry(services)

    assert registry.platform_document.list_documents(active_only=None).ok is True
    assert registry.platform_party.list_parties(active_only=None).ok is True
    assert registry.platform_support.load_settings().ok is True
    assert registry.platform_user.list_users().ok is True
