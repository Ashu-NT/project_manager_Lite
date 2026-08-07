from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
    DocumentStorageKind,
    DocumentStructure,
    DocumentType,
)


def test_document_structure_dto_normalizes_and_validates_fields() -> None:
    structure = DocumentStructure.create(
        organization_id="  org-1  ",
        structure_code="  asset manuals  ",
        name="  Asset Manuals  ",
        description="  Main library  ",
        parent_structure_id="  parent-1  ",
        object_scope="  asset category  ",
        default_document_type="manual",
        sort_order="5",
        notes="  Managed by engineering  ",
    )

    assert structure.organization_id == "org-1"
    assert structure.structure_code == "ASSET_MANUALS"
    assert structure.name == "Asset Manuals"
    assert structure.description == "Main library"
    assert structure.parent_structure_id == "parent-1"
    assert structure.object_scope == "ASSET_CATEGORY"
    assert structure.default_document_type is DocumentType.MANUAL
    assert structure.sort_order == 5
    assert structure.notes == "Managed by engineering"

    structure.version = "2"
    assert structure.version == 2

    with pytest.raises(ValidationError) as exc_version:
        structure.version = 0
    assert exc_version.value.code == "DOCUMENT_STRUCTURE_VERSION_INVALID"


def test_document_dto_normalizes_and_validates_fields() -> None:
    document = Document.create(
        organization_id="  org-1  ",
        document_code="  man-001  ",
        title="  Pump Manual  ",
        document_type="manual",
        document_structure_id="  structure-1  ",
        storage_kind="external_url",
        storage_uri="  https://example.test/pump-manual.pdf  ",
        file_name="  pump-manual.pdf  ",
        mime_type="  application/pdf  ",
        source_system="  sharepoint  ",
        uploaded_at=datetime(2026, 7, 10, 9, 30, 0),
        uploaded_by_user_id="  user-1  ",
        effective_date=date(2026, 7, 1),
        review_date=date(2026, 7, 31),
        confidentiality_level="  internal  ",
        revision="  Rev B  ",
        notes="  Controlled copy  ",
    )

    assert document.organization_id == "org-1"
    assert document.document_code == "MAN-001"
    assert document.title == "Pump Manual"
    assert document.document_type is DocumentType.MANUAL
    assert document.classification is DocumentType.MANUAL
    assert document.document_structure_id == "structure-1"
    assert document.storage_kind is DocumentStorageKind.EXTERNAL_URL
    assert document.storage_uri == "https://example.test/pump-manual.pdf"
    assert document.file_name == "pump-manual.pdf"
    assert document.mime_type == "application/pdf"
    assert document.source_system == "sharepoint"
    assert document.uploaded_at == datetime(2026, 7, 10, 9, 30, 0, tzinfo=timezone.utc)
    assert document.uploaded_by_user_id == "user-1"
    assert document.confidentiality_level == "INTERNAL"
    assert document.business_version_label == "Rev B"
    assert document.revision == "Rev B"
    assert document.notes == "Controlled copy"

    document.storage_ref = "  C:/docs/pump-manual-v2.pdf  "
    document.classification = "policy"
    document.version = "2"

    assert document.storage_uri == "C:/docs/pump-manual-v2.pdf"
    assert document.document_type is DocumentType.POLICY
    assert document.version == 2

    with pytest.raises(ValidationError) as exc_range:
        Document.create(
            organization_id="org-1",
            document_code="DOC-002",
            title="Bad Window",
            storage_uri="vault://bad-window",
            effective_date=date(2026, 8, 1),
            review_date=date(2026, 7, 1),
        )
    assert exc_range.value.code == "DOCUMENT_REVIEW_DATE_INVALID"

    with pytest.raises(ValidationError) as exc_storage:
        Document.create(
            organization_id="org-1",
            document_code="DOC-003",
            title="Missing Storage",
            storage_uri="  ",
        )
    assert exc_storage.value.code == "DOCUMENT_STORAGE_REF_REQUIRED"


def test_document_link_dto_normalizes_and_validates_fields() -> None:
    link = DocumentLink.create(
        organization_id="  org-1  ",
        document_id="  doc-1  ",
        module_code="  MAINTENANCE_MANAGEMENT  ",
        entity_type="  asset  ",
        entity_id="  asset-001  ",
        link_role="  reference  ",
    )

    assert link.organization_id == "org-1"
    assert link.document_id == "doc-1"
    assert link.module_code == "maintenance_management"
    assert link.entity_type == "asset"
    assert link.entity_id == "asset-001"
    assert link.link_role == "reference"

    with pytest.raises(ValidationError) as exc_module:
        DocumentLink.create(
            organization_id="org-1",
            document_id="doc-1",
            module_code="  ",
            entity_type="asset",
            entity_id="asset-001",
        )
    assert exc_module.value.code == "DOCUMENT_MODULE_REQUIRED"
