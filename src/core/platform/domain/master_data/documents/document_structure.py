from __future__ import annotations

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.domain.master_data.documents.document import DocumentType


def _normalize_document_type(value: object) -> DocumentType:
    if isinstance(value, DocumentType):
        return value
    raw = normalize_optional_text(value).upper() or DocumentType.GENERAL.value
    try:
        return DocumentType(raw)
    except ValueError as exc:
        raise ValidationError(
            "Document type is invalid.",
            code="DOCUMENT_TYPE_INVALID",
        ) from exc


def _normalize_sort_order(value: object) -> int:
    try:
        return int(value if value not in (None, "") else 0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Document structure sort order must be an integer.",
            code="DOCUMENT_STRUCTURE_SORT_ORDER_INVALID",
        ) from exc


def _normalize_positive_int(value: object, *, code: str, message: str) -> int:
    try:
        resolved = int(value if value not in (None, "") else 1)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 1:
        raise ValidationError(message, code=code)
    return resolved


@validated_dataclass
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

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="DOCUMENT_STRUCTURE_ORGANIZATION_REQUIRED",
        )

    @field_validator("structure_code", mode="before")
    @classmethod
    def _validate_structure_code(cls, value: object) -> str:
        return (
            normalize_required_text(
                value,
                message="Document structure code is required.",
                code="DOCUMENT_STRUCTURE_CODE_REQUIRED",
            )
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Document structure name is required.",
            code="DOCUMENT_STRUCTURE_NAME_REQUIRED",
        )

    @field_validator("description", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("parent_structure_id", mode="before")
    @classmethod
    def _normalize_parent_structure_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("object_scope", mode="before")
    @classmethod
    def _normalize_object_scope(cls, value: object) -> str:
        normalized = (
            normalize_optional_text(value)
            .upper()
            .replace(" ", "_")
            .replace("-", "_")
        )
        return normalized or "GENERAL"

    @field_validator("default_document_type", mode="before")
    @classmethod
    def _validate_default_document_type(cls, value: object) -> DocumentType:
        return _normalize_document_type(value)

    @field_validator("sort_order", mode="before")
    @classmethod
    def _validate_sort_order(cls, value: object) -> int:
        return _normalize_sort_order(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="DOCUMENT_STRUCTURE_VERSION_INVALID",
            message="Document structure version must be positive.",
        )

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
            sort_order=sort_order,
            is_active=is_active,
            notes=notes,
            version=1,
        )


__all__ = ["DocumentStructure"]
