from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


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


def _normalize_storage_kind(value: object) -> DocumentStorageKind:
    if isinstance(value, DocumentStorageKind):
        return value
    raw = normalize_optional_text(value).upper() or DocumentStorageKind.FILE_PATH.value
    try:
        return DocumentStorageKind(raw)
    except ValueError as exc:
        raise ValidationError(
            "Document storage kind is invalid.",
            code="DOCUMENT_STORAGE_KIND_INVALID",
        ) from exc


def _normalize_optional_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValidationError(
            "Document dates must be valid dates.",
            code="DOCUMENT_DATE_INVALID",
        )
    return value


def _normalize_optional_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Document timestamps must be valid datetimes.",
            code="DOCUMENT_TIMESTAMP_INVALID",
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_positive_int(value: object, *, code: str, message: str) -> int:
    try:
        resolved = int(value if value not in (None, "") else 1)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 1:
        raise ValidationError(message, code=code)
    return resolved


@validated_dataclass
class Document:
    id: str
    organization_id: str
    document_code: str
    title: str
    document_type: DocumentType = DocumentType.GENERAL
    document_structure_id: str | None = None
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
    business_version_label: str = ""
    is_current: bool = True
    notes: str = ""
    is_active: bool = True
    version: int = 1

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="DOCUMENT_ORGANIZATION_REQUIRED",
        )

    @field_validator("document_code", mode="before")
    @classmethod
    def _validate_document_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Document code is required.",
            code="DOCUMENT_CODE_REQUIRED",
        ).upper()

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Document title is required.",
            code="DOCUMENT_TITLE_REQUIRED",
        )

    @field_validator("document_type", mode="before")
    @classmethod
    def _validate_document_type(cls, value: object) -> DocumentType:
        return _normalize_document_type(value)

    @field_validator("document_structure_id", "uploaded_by_user_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("storage_kind", mode="before")
    @classmethod
    def _validate_storage_kind(cls, value: object) -> DocumentStorageKind:
        return _normalize_storage_kind(value)

    @field_validator("storage_uri", mode="before")
    @classmethod
    def _validate_storage_uri(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Document storage URI is required.",
            code="DOCUMENT_STORAGE_REF_REQUIRED",
        )

    @field_validator(
        "file_name",
        "mime_type",
        "business_version_label",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("source_system", mode="before")
    @classmethod
    def _normalize_source_system(cls, value: object) -> str:
        return normalize_optional_text(value) or "platform"

    @field_validator("uploaded_at", mode="before")
    @classmethod
    def _validate_uploaded_at(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(value)

    @field_validator("effective_date", "review_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("confidentiality_level", mode="before")
    @classmethod
    def _normalize_confidentiality_level(cls, value: object) -> str:
        return normalize_optional_text(value).upper()

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="DOCUMENT_VERSION_INVALID",
            message="Document version must be positive.",
        )

    @model_validator(mode="after")
    def _validate_date_window(self) -> "Document":
        if (
            self.effective_date is not None
            and self.review_date is not None
            and self.review_date < self.effective_date
        ):
            raise ValidationError(
                "Document review date cannot be earlier than the effective date.",
                code="DOCUMENT_REVIEW_DATE_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        document_code: str,
        title: str,
        document_type: DocumentType = DocumentType.GENERAL,
        document_structure_id: str | None = None,
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
        business_version_label: str = "",
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
            document_structure_id=document_structure_id,
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
            business_version_label=business_version_label or revision,
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
    def revision(self) -> str:
        return self.business_version_label

    @revision.setter
    def revision(self, value: str) -> None:
        self.business_version_label = value

    @property
    def storage_ref(self) -> str:
        return self.storage_uri

    @storage_ref.setter
    def storage_ref(self, value: str) -> None:
        self.storage_uri = value


__all__ = [
    "Document",
    "DocumentClassification",
    "DocumentStorageKind",
    "DocumentType",
]
