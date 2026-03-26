from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from core.platform.common.ids import generate_id


class DocumentType(str, Enum):
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


DocumentClassification = DocumentType


@dataclass
class Document:
    id: str
    organization_id: str
    document_code: str
    title: str
    document_type: DocumentType = DocumentType.GENERAL
    storage_kind: DocumentStorageKind = DocumentStorageKind.FILE_PATH
    storage_uri: str = ""
    file_name: str = ""
    mime_type: str = ""
    source_system: str = ""
    uploaded_at: datetime | None = None
    uploaded_by_user_id: str | None = None
    effective_date: date | None = None
    review_date: date | None = None
    confidentiality_level: str = ""
    revision: str = ""
    is_current: bool = True
    notes: str = ""
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        document_code: str,
        title: str,
        document_type: DocumentType = DocumentType.GENERAL,
        storage_kind: DocumentStorageKind = DocumentStorageKind.FILE_PATH,
        storage_uri: str = "",
        file_name: str = "",
        mime_type: str = "",
        source_system: str = "",
        uploaded_at: datetime | None = None,
        uploaded_by_user_id: str | None = None,
        effective_date: date | None = None,
        review_date: date | None = None,
        confidentiality_level: str = "",
        revision: str = "",
        is_current: bool = True,
        notes: str = "",
        is_active: bool = True,
    ) -> "Document":
        now = datetime.now(timezone.utc)
        return Document(
            id=generate_id(),
            organization_id=organization_id,
            document_code=document_code,
            title=title,
            document_type=document_type,
            storage_kind=storage_kind,
            storage_uri=storage_uri,
            file_name=file_name,
            mime_type=mime_type,
            source_system=source_system,
            uploaded_at=uploaded_at or now,
            uploaded_by_user_id=uploaded_by_user_id,
            effective_date=effective_date,
            review_date=review_date,
            confidentiality_level=confidentiality_level,
            revision=revision,
            is_current=is_current,
            notes=notes,
            is_active=is_active,
            version=1,
        )

    @property
    def classification(self) -> DocumentType:
        return self.document_type

    @classification.setter
    def classification(self, value: DocumentType) -> None:
        self.document_type = value

    @property
    def storage_ref(self) -> str:
        return self.storage_uri

    @storage_ref.setter
    def storage_ref(self, value: str) -> None:
        self.storage_uri = value


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
    "DocumentType",
]
