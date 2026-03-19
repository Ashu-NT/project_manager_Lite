from __future__ import annotations

from core.platform.documents.domain import (
    Document,
    DocumentClassification,
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
        classification=document.classification.value,
        storage_kind=document.storage_kind.value,
        storage_ref=document.storage_ref,
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
        classification=DocumentClassification(obj.classification),
        storage_kind=DocumentStorageKind(obj.storage_kind),
        storage_ref=obj.storage_ref or "",
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
