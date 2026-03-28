from __future__ import annotations

from core.platform.common.exceptions import ValidationError


def test_document_service_scopes_documents_by_active_organization(services):
    organization_service = services["organization_service"]
    document_service = services["document_service"]

    default_organization = organization_service.get_active_organization()
    created = document_service.create_document(
        document_code="MAN-001",
        title="Operations Manual",
        document_type="MANUAL",
        storage_kind="FILE_PATH",
        storage_uri="C:/docs/manual.pdf",
        confidentiality_level="INTERNAL",
        revision="R1",
    )

    assert created.organization_id == default_organization.id
    assert created.document_type.value == "MANUAL"
    assert created.storage_uri == "C:/docs/manual.pdf"
    assert created.file_name == "manual.pdf"
    assert created.source_system == "platform"
    assert created.uploaded_by_user_id is not None
    assert created.is_current is True
    assert created.revision == "R1"
    assert created.confidentiality_level == "INTERNAL"
    assert [document.title for document in document_service.list_documents()] == ["Operations Manual"]

    second_organization = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    assert document_service.get_context_organization().display_name == "Operations Hub"
    assert document_service.list_documents() == []


def test_document_service_links_documents_to_module_entities(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code="DRW-001",
        title="Pump Drawing",
        document_type="DRAWING",
        storage_kind="REFERENCE",
        storage_uri="vault://pump/drawing-001",
    )

    link = document_service.add_link(
        document_id=document.id,
        module_code="maintenance_management",
        entity_type="asset",
        entity_id="asset-001",
        link_role="reference",
    )

    assert link.module_code == "maintenance_management"
    assert [item.entity_id for item in document_service.list_links(document.id)] == ["asset-001"]
    assert [item.document_id for item in document_service.list_links_for_entity(
        module_code="maintenance_management",
        entity_type="asset",
        entity_id="asset-001",
    )] == [document.id]


def test_document_service_rejects_duplicate_codes_and_links(services):
    document_service = services["document_service"]
    document_service.create_document(
        document_code="DOC-001",
        title="Policy",
        document_type="POLICY",
        storage_kind="EXTERNAL_URL",
        storage_uri="https://example.test/policy",
    )

    try:
        document_service.create_document(
            document_code="DOC-001",
            title="Second Policy",
            document_type="POLICY",
            storage_kind="EXTERNAL_URL",
            storage_uri="https://example.test/other-policy",
        )
    except ValidationError as exc:
        assert exc.code == "DOCUMENT_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate document code validation error.")

    document = document_service.list_documents()[0]
    document_service.add_link(
        document_id=document.id,
        module_code="project_management",
        entity_type="task_comment",
        entity_id="comment-1",
        link_role="attachment",
    )
    try:
        document_service.add_link(
            document_id=document.id,
            module_code="project_management",
            entity_type="task_comment",
            entity_id="comment-1",
            link_role="attachment",
        )
    except ValidationError as exc:
        assert exc.code == "DOCUMENT_LINK_EXISTS"
    else:
        raise AssertionError("Expected duplicate document link validation error.")


def test_document_service_updates_and_unlinks_documents(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code="DOC-002",
        title="Checklist",
        document_type="PROCEDURE",
        storage_kind="FILE_PATH",
        storage_uri="C:/docs/checklist.docx",
        source_system="sharepoint",
        revision="R0",
    )
    link = document_service.add_link(
        document_id=document.id,
        module_code="qhse",
        entity_type="inspection",
        entity_id="inspection-77",
        link_role="evidence",
    )

    updated = document_service.update_document(
        document.id,
        title="Inspection Checklist",
        revision="R2",
        confidentiality_level="CONFIDENTIAL",
        is_active=False,
        expected_version=document.version,
    )

    assert updated.title == "Inspection Checklist"
    assert updated.revision == "R2"
    assert updated.confidentiality_level == "CONFIDENTIAL"
    assert updated.source_system == "sharepoint"
    assert updated.is_active is False

    document_service.remove_link(link.id)
    assert document_service.list_links(document.id) == []


def test_document_service_infers_mime_type_from_storage_path(services, tmp_path):
    document_service = services["document_service"]
    pdf_path = tmp_path / "pump-manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    document = document_service.create_document(
        document_code="DOC-PDF",
        title="Pump Manual",
        document_type="MANUAL",
        storage_kind="FILE_PATH",
        storage_uri=str(pdf_path),
    )

    assert document.file_name == "pump-manual.pdf"
    assert document.mime_type == "application/pdf"
