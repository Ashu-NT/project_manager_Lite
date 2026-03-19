from __future__ import annotations

from core.platform.documents.domain import (
    Document,
    DocumentType,
    DocumentLink,
    DocumentStorageKind,
)
from infra.platform.db.models import DocumentLinkORM, DocumentORM


def document_to_orm(document: Document) -> DocumentORM:
    return DocumentORM(
        id=document.id,
        organization_id=document.organization_id,
        document_code=document.document_code,
        title=document.title,
        document_type=document.document_type.value,
        storage_kind=document.storage_kind.value,
        storage_uri=document.storage_uri,
        file_name=document.file_name or None,
        mime_type=document.mime_type or None,
        source_system=document.source_system or None,
        uploaded_at=document.uploaded_at,
        uploaded_by_user_id=document.uploaded_by_user_id,
        effective_date=document.effective_date,
        review_date=document.review_date,
        confidentiality_level=document.confidentiality_level or None,
        revision=document.revision or None,
        is_current=document.is_current,
        notes=document.notes or None,
        is_active=document.is_active,
        version=getattr(document, "version", 1),
    )


def document_from_orm(obj: DocumentORM) -> Document:
    return Document(
        id=obj.id,
        organization_id=obj.organization_id,
        document_code=obj.document_code,
        title=obj.title,
        document_type=DocumentType(obj.document_type),
        storage_kind=DocumentStorageKind(obj.storage_kind),
        storage_uri=obj.storage_uri or "",
        file_name=obj.file_name or "",
        mime_type=obj.mime_type or "",
        source_system=obj.source_system or "",
        uploaded_at=obj.uploaded_at,
        uploaded_by_user_id=obj.uploaded_by_user_id,
        effective_date=obj.effective_date,
        review_date=obj.review_date,
        confidentiality_level=obj.confidentiality_level or "",
        revision=obj.revision or "",
        is_current=obj.is_current,
        notes=obj.notes or "",
        is_active=obj.is_active,
        version=getattr(obj, "version", 1),
    )


def document_link_to_orm(link: DocumentLink) -> DocumentLinkORM:
    return DocumentLinkORM(
        id=link.id,
        organization_id=link.organization_id,
        document_id=link.document_id,
        module_code=link.module_code,
        entity_type=link.entity_type,
        entity_id=link.entity_id,
        link_role=link.link_role or None,
    )


def document_link_from_orm(obj: DocumentLinkORM) -> DocumentLink:
    return DocumentLink(
        id=obj.id,
        organization_id=obj.organization_id,
        document_id=obj.document_id,
        module_code=obj.module_code,
        entity_type=obj.entity_type,
        entity_id=obj.entity_id,
        link_role=obj.link_role or "",
    )


__all__ = [
    "document_from_orm",
    "document_link_from_orm",
    "document_link_to_orm",
    "document_to_orm",
]
