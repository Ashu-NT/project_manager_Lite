from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.modules.project_management.domain.identifiers import generate_id


class DocumentClassification(str, Enum):
    GENERAL = "GENERAL"
    MANUAL = "MANUAL"
    DATASHEET = "DATASHEET"
    DRAWING = "DRAWING"
    PROCEDURE = "PROCEDURE"
    POLICY = "POLICY"
    CERTIFICATE = "CERTIFICATE"


class DocumentStorageKind(str, Enum):
    FILE_PATH = "FILE_PATH"
    EXTERNAL_URL = "EXTERNAL_URL"
    REFERENCE = "REFERENCE"


@dataclass
class Document:
    id: str
    organization_id: str
    document_code: str
    title: str
    classification: DocumentClassification = DocumentClassification.GENERAL
    storage_kind: DocumentStorageKind = DocumentStorageKind.FILE_PATH
    storage_ref: str = ""
    notes: str = ""
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        document_code: str,
        title: str,
        classification: DocumentClassification = DocumentClassification.GENERAL,
        storage_kind: DocumentStorageKind = DocumentStorageKind.FILE_PATH,
        storage_ref: str = "",
        notes: str = "",
        is_active: bool = True,
    ) -> "Document":
        return Document(
            id=generate_id(),
            organization_id=organization_id,
            document_code=document_code,
            title=title,
            classification=classification,
            storage_kind=storage_kind,
            storage_ref=storage_ref,
            notes=notes,
            is_active=is_active,
            version=1,
        )


@dataclass
class DocumentLink:
    id: str
    organization_id: str
    document_id: str
    module_code: str
    entity_type: str
    entity_id: str
    link_role: str = ""

    @staticmethod
    def create(
        *,
        organization_id: str,
        document_id: str,
        module_code: str,
        entity_type: str,
        entity_id: str,
        link_role: str = "",
    ) -> "DocumentLink":
        return DocumentLink(
            id=generate_id(),
            organization_id=organization_id,
            document_id=document_id,
            module_code=module_code,
            entity_type=entity_type,
            entity_id=entity_id,
            link_role=link_role,
        )


__all__ = [
    "Document",
    "DocumentClassification",
    "DocumentLink",
    "DocumentStorageKind",
]
