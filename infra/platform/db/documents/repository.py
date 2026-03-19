from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.documents.domain import Document, DocumentLink
from core.platform.documents.interfaces import DocumentLinkRepository, DocumentRepository
from infra.platform.db.documents.mapper import (
    document_from_orm,
    document_link_from_orm,
    document_link_to_orm,
    document_to_orm,
)
from infra.platform.db.models import DocumentLinkORM, DocumentORM
from infra.platform.db.optimistic import update_with_version_check


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, document: Document) -> None:
        self.session.add(document_to_orm(document))

    def update(self, document: Document) -> None:
        document.version = update_with_version_check(
            self.session,
            DocumentORM,
            document.id,
            getattr(document, "version", 1),
            {
                "document_code": document.document_code,
                "title": document.title,
                "document_type": document.document_type.value,
                "storage_kind": document.storage_kind.value,
                "storage_uri": document.storage_uri,
                "file_name": document.file_name or None,
                "mime_type": document.mime_type or None,
                "source_system": document.source_system or None,
                "uploaded_at": document.uploaded_at,
                "uploaded_by_user_id": document.uploaded_by_user_id,
                "effective_date": document.effective_date,
                "review_date": document.review_date,
                "confidentiality_level": document.confidentiality_level or None,
                "revision": document.revision or None,
                "is_current": document.is_current,
                "notes": document.notes or None,
                "is_active": document.is_active,
            },
            not_found_message="Document not found.",
            stale_message="Document was updated by another user.",
        )

    def get(self, document_id: str) -> Document | None:
        obj = self.session.get(DocumentORM, document_id)
        return document_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, document_code: str) -> Document | None:
        stmt = select(DocumentORM).where(
            DocumentORM.organization_id == organization_id,
            DocumentORM.document_code == document_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return document_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Document]:
        stmt = select(DocumentORM).where(DocumentORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(DocumentORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(DocumentORM.title.asc())).scalars().all()
        return [document_from_orm(row) for row in rows]


class SqlAlchemyDocumentLinkRepository(DocumentLinkRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, link: DocumentLink) -> None:
        self.session.add(document_link_to_orm(link))

    def get(self, link_id: str) -> DocumentLink | None:
        obj = self.session.get(DocumentLinkORM, link_id)
        return document_link_from_orm(obj) if obj else None

    def list_for_document(self, document_id: str) -> list[DocumentLink]:
        stmt = select(DocumentLinkORM).where(DocumentLinkORM.document_id == document_id)
        rows = self.session.execute(
            stmt.order_by(
                DocumentLinkORM.module_code.asc(),
                DocumentLinkORM.entity_type.asc(),
                DocumentLinkORM.entity_id.asc(),
                DocumentLinkORM.link_role.asc(),
            )
        ).scalars().all()
        return [document_link_from_orm(row) for row in rows]

    def list_for_entity(self, organization_id: str, module_code: str, entity_type: str, entity_id: str) -> list[DocumentLink]:
        stmt = select(DocumentLinkORM).where(
            DocumentLinkORM.organization_id == organization_id,
            DocumentLinkORM.module_code == module_code,
            DocumentLinkORM.entity_type == entity_type,
            DocumentLinkORM.entity_id == entity_id,
        )
        rows = self.session.execute(stmt.order_by(DocumentLinkORM.document_id.asc())).scalars().all()
        return [document_link_from_orm(row) for row in rows]

    def find_existing(
        self,
        *,
        document_id: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        link_role: str,
    ) -> DocumentLink | None:
        stmt = select(DocumentLinkORM).where(
            DocumentLinkORM.document_id == document_id,
            DocumentLinkORM.module_code == module_code,
            DocumentLinkORM.entity_type == entity_type,
            DocumentLinkORM.entity_id == entity_id,
            DocumentLinkORM.link_role == (link_role or None),
        )
        obj = self.session.execute(stmt).scalars().first()
        return document_link_from_orm(obj) if obj else None

    def delete(self, link_id: str) -> None:
        obj = self.session.get(DocumentLinkORM, link_id)
        if obj is not None:
            self.session.delete(obj)


__all__ = ["SqlAlchemyDocumentLinkRepository", "SqlAlchemyDocumentRepository"]
