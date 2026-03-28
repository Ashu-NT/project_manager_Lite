from __future__ import annotations

from mimetypes import guess_type
from pathlib import Path

from core.platform.common.exceptions import ValidationError
from core.platform.documents.domain import DocumentStorageKind, DocumentType


def normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def normalize_module_code(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        raise ValidationError("Module code is required.", code="DOCUMENT_MODULE_REQUIRED")
    return normalized


def normalize_entity_label(value: str, *, code: str, label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=code)
    return normalized


def coerce_document_type(value: DocumentType | str | None) -> DocumentType:
    if isinstance(value, DocumentType):
        return value
    raw = str(value or DocumentType.GENERAL.value).strip().upper()
    try:
        return DocumentType(raw)
    except ValueError as exc:
        raise ValidationError("Document type is invalid.", code="DOCUMENT_TYPE_INVALID") from exc


def coerce_storage_kind(value: DocumentStorageKind | str | None) -> DocumentStorageKind:
    if isinstance(value, DocumentStorageKind):
        return value
    raw = str(value or DocumentStorageKind.FILE_PATH.value).strip().upper()
    try:
        return DocumentStorageKind(raw)
    except ValueError as exc:
        raise ValidationError("Document storage kind is invalid.", code="DOCUMENT_STORAGE_KIND_INVALID") from exc


def normalize_confidentiality(value: str | None) -> str:
    return normalize_optional_text(value).upper()


def normalize_structure_code(value: str) -> str:
    normalized = normalize_optional_text(value).upper().replace(" ", "_").replace("-", "_")
    if not normalized:
        raise ValidationError("Document structure code is required.", code="DOCUMENT_STRUCTURE_CODE_REQUIRED")
    return normalized


def normalize_structure_name(value: str) -> str:
    normalized = normalize_optional_text(value)
    if not normalized:
        raise ValidationError("Document structure name is required.", code="DOCUMENT_STRUCTURE_NAME_REQUIRED")
    return normalized


def normalize_object_scope(value: str | None) -> str:
    normalized = normalize_optional_text(value).upper().replace(" ", "_").replace("-", "_")
    return normalized or "GENERAL"


def default_file_name(storage_uri: str, explicit_file_name: str | None) -> str:
    normalized = normalize_optional_text(explicit_file_name)
    if normalized:
        return normalized
    candidate = storage_uri.rstrip("/\\").split("/")[-1].split("\\")[-1]
    return candidate.split("?")[0].strip()


def infer_storage_kind(storage_uri: str) -> DocumentStorageKind:
    normalized = normalize_optional_text(storage_uri)
    lowered = normalized.lower()
    if lowered.startswith(("http://", "https://")):
        return DocumentStorageKind.EXTERNAL_URL
    candidate = Path(normalized)
    if candidate.exists() and candidate.is_file():
        return DocumentStorageKind.FILE_PATH
    return DocumentStorageKind.REFERENCE


def infer_file_name(storage_uri: str) -> str:
    return default_file_name(storage_uri, None) or Path(storage_uri).name or normalize_optional_text(storage_uri)


def infer_title(storage_uri: str) -> str:
    return infer_file_name(storage_uri) or normalize_optional_text(storage_uri) or "Attachment"


def infer_mime_type(storage_uri: str) -> str:
    mime_type, _encoding = guess_type(storage_uri)
    return normalize_optional_text(mime_type)


__all__ = [
    "coerce_document_type",
    "coerce_storage_kind",
    "default_file_name",
    "infer_file_name",
    "infer_mime_type",
    "infer_storage_kind",
    "normalize_object_scope",
    "infer_title",
    "normalize_confidentiality",
    "normalize_entity_label",
    "normalize_module_code",
    "normalize_optional_text",
    "normalize_structure_code",
    "normalize_structure_name",
]
