from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.documents.contracts import (
    DocumentLinkRepository,
    DocumentRepository,
    DocumentStructureRepository,
)
from src.core.platform.documents.domain import Document, DocumentLink, DocumentStructure
from src.core.platform.infrastructure.persistence.mappers.documents import (
    document_from_orm,
    document_link_from_orm,
    document_link_to_orm,
    document_structure_from_orm,
    document_structure_to_orm,
    document_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.documents import DocumentLinkORM, DocumentORM, DocumentStructureORM
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyDocumentStructureRepository(DocumentStructureRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, structure: DocumentStructure) -> None:
        self.session.add(document_structure_to_orm(structure))

    def update(self, structure: DocumentStructure) -> None:
        structure.version = update_with_version_check(
            self.session,
            DocumentStructureORM,
            structure.id,
            getattr(structure, "version", 1),
            {
                "structure_code": structure.structure_code,
                "name": structure.name,
                "description": structure.description or None,
                "parent_structure_id": structure.parent_structure_id,
                "object_scope": structure.object_scope,
                "default_document_type": structure.default_document_type.value,
                "sort_order": structure.sort_order,
                "is_active": structure.is_active,
                "notes": structure.notes or None,
            },
            not_found_message="Document structure not found.",
            stale_message="Document structure was updated by another user.",
        )

    def get(self, structure_id: str) -> DocumentStructure | None:
        obj = self.session.get(DocumentStructureORM, structure_id)
        return document_structure_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, structure_code: str) -> DocumentStructure | None:
        stmt = select(DocumentStructureORM).where(
            DocumentStructureORM.organization_id == organization_id,
            DocumentStructureORM.structure_code == structure_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return document_structure_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        object_scope: str | None = None,
    ) -> list[DocumentStructure]:
        stmt = select(DocumentStructureORM).where(DocumentStructureORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(DocumentStructureORM.is_active == bool(active_only))
        if object_scope is not None:
            stmt = stmt.where(DocumentStructureORM.object_scope == object_scope)
        rows = self.session.execute(
            stmt.order_by(
                DocumentStructureORM.sort_order.asc(),
                DocumentStructureORM.name.asc(),
            )
        ).scalars().all()
        return [document_structure_from_orm(row) for row in rows]


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
                "document_structure_id": document.document_structure_id,
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
                "business_version_label": document.business_version_label or None,
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

    def list_for_module(
        self,
        organization_id: str,
        module_code: str,
        *,
        entity_type: str | None = None,
    ) -> list[DocumentLink]:
        stmt = select(DocumentLinkORM).where(
            DocumentLinkORM.organization_id == organization_id,
            DocumentLinkORM.module_code == module_code,
        )
        if entity_type is not None:
            stmt = stmt.where(DocumentLinkORM.entity_type == entity_type)
        rows = self.session.execute(
            stmt.order_by(
                DocumentLinkORM.entity_type.asc(),
                DocumentLinkORM.entity_id.asc(),
                DocumentLinkORM.document_id.asc(),
            )
        ).scalars().all()
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


__all__ = [
    "SqlAlchemyDocumentLinkRepository",
    "SqlAlchemyDocumentRepository",
    "SqlAlchemyDocumentStructureRepository",
]
