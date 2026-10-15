from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.domain.master_data.documents import (
    DocumentType,
)


@dataclass(frozen=True)
class DocumentStructureCreateCommand:
    structure_code: str
    name: str
    description: str = ""
    parent_structure_id: str | None = None
    object_scope: str = "GENERAL"
    default_document_type: DocumentType | str | None = None
    sort_order: int = 0
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class DocumentStructureUpdateCommand:
    structure_id: str
    structure_code: str | None = None
    name: str | None = None
    description: str | None = None
    parent_structure_id: str | None = None
    object_scope: str | None = None
    default_document_type: DocumentType | str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None
