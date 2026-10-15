from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.core.platform.domain.master_data.documents import (
    DocumentStorageKind,
    DocumentType,
)


@dataclass(frozen=True)
class DocumentCreateCommand:
    document_code: str
    title: str
    document_type: DocumentType | str = DocumentType.GENERAL
    document_structure_id: str | None = None
    storage_kind: DocumentStorageKind | str = DocumentStorageKind.FILE_PATH
    storage_uri: str = ""
    file_name: str = ""
    mime_type: str = ""
    source_system: str = ""
    uploaded_at: datetime | None = None
    uploaded_by_user_id: str | None = None
    effective_date: date | None = None
    review_date: date | None = None
    confidentiality_level: str = ""
    business_version_label: str = ""
    is_current: bool = True
    notes: str = ""
    is_active: bool = True


@dataclass(frozen=True)
class DocumentUpdateCommand:
    document_id: str
    document_code: str | None = None
    title: str | None = None
    document_type: DocumentType | str | None = None
    document_structure_id: str | None = None
    storage_kind: DocumentStorageKind | str | None = None
    storage_uri: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    source_system: str | None = None
    uploaded_at: datetime | None = None
    uploaded_by_user_id: str | None = None
    effective_date: date | None = None
    review_date: date | None = None
    confidentiality_level: str | None = None
    business_version_label: str | None = None
    is_current: bool | None = None
    notes: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None
