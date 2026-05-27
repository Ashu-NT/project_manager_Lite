from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.common.ids import generate_id
from src.core.platform.documents.domain.document import DocumentType


@dataclass
class DocumentStructure:
    id: str
    organization_id: str
    structure_code: str
    name: str
    description: str = ""
    parent_structure_id: str | None = None
    object_scope: str = "GENERAL"
    default_document_type: DocumentType = DocumentType.GENERAL
    sort_order: int = 0
    is_active: bool = True
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        structure_code: str,
        name: str,
        description: str = "",
        parent_structure_id: str | None = None,
        object_scope: str = "GENERAL",
        default_document_type: DocumentType = DocumentType.GENERAL,
        sort_order: int = 0,
        is_active: bool = True,
        notes: str = "",
    ) -> "DocumentStructure":
        return DocumentStructure(
            id=generate_id(),
            organization_id=organization_id,
            structure_code=structure_code,
            name=name,
            description=description,
            parent_structure_id=parent_structure_id,
            object_scope=object_scope,
            default_document_type=default_document_type,
            sort_order=int(sort_order or 0),
            is_active=bool(is_active),
            notes=notes,
            version=1,
        )


__all__ = ["DocumentStructure"]
