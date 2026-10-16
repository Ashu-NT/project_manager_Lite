from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.master_data.documents.queries.document_queries import (
        DocumentPage,
        EntityDocumentPage,
    )

from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentDto,
    DocumentLinkDto,
    DocumentPageDto,
    DocumentStructureDto,
)
from src.core.platform.domain.master_data.documents import (
    Document,
    DocumentLink,
    DocumentStructure,
)


def serialize_document_page(page: DocumentPage) -> DocumentPageDto:
    return DocumentPageDto(
        items=tuple(serialize_document(document) for document in page.items),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )


def serialize_entity_document_page(page: EntityDocumentPage) -> DocumentPageDto:
    return DocumentPageDto(
        items=tuple(
            serialize_document(row.document, link_id=row.link.id) for row in page.items
        ),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )




def serialize_document(document: Document, *, link_id: str = "") -> DocumentDto:
    return DocumentDto(
        id=document.id,
        organization_id=document.organization_id,
        document_code=document.document_code,
        title=document.title,
        document_type=document.document_type,
        document_structure_id=document.document_structure_id,
        storage_kind=document.storage_kind,
        storage_uri=document.storage_uri,
        file_name=document.file_name,
        mime_type=document.mime_type,
        source_system=document.source_system,
        uploaded_at=document.uploaded_at,
        uploaded_by_user_id=document.uploaded_by_user_id,
        effective_date=document.effective_date,
        review_date=document.review_date,
        confidentiality_level=document.confidentiality_level,
        business_version_label=document.business_version_label,
        is_current=document.is_current,
        notes=document.notes,
        is_active=document.is_active,
        version=document.version,
        link_id=link_id,
    )


def serialize_document_structure(structure: DocumentStructure) -> DocumentStructureDto:
    return DocumentStructureDto(
        id=structure.id,
        organization_id=structure.organization_id,
        structure_code=structure.structure_code,
        name=structure.name,
        description=structure.description,
        parent_structure_id=structure.parent_structure_id,
        object_scope=structure.object_scope,
        default_document_type=structure.default_document_type,
        sort_order=structure.sort_order,
        is_active=structure.is_active,
        notes=structure.notes,
        version=structure.version,
    )


def serialize_document_link(link: DocumentLink) -> DocumentLinkDto:
    return DocumentLinkDto(
        id=link.id,
        organization_id=link.organization_id,
        document_id=link.document_id,
        module_code=link.module_code,
        entity_type=link.entity_type,
        entity_id=link.entity_id,
        link_role=link.link_role,
    )
