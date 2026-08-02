from __future__ import annotations

from pydantic import field_validator

from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.common.ids import generate_id


def normalize_document_module_code(value: object) -> str:
    return normalize_required_text(
        value,
        message="Module code is required.",
        code="DOCUMENT_MODULE_REQUIRED",
    ).lower()


def normalize_document_entity_type(value: object) -> str:
    return normalize_required_text(
        value,
        message="Entity type is required.",
        code="DOCUMENT_ENTITY_TYPE_REQUIRED",
    )


def normalize_document_entity_id(value: object) -> str:
    return normalize_required_text(
        value,
        message="Entity id is required.",
        code="DOCUMENT_ENTITY_ID_REQUIRED",
    )


def normalize_document_link_role(value: object) -> str:
    return normalize_optional_text(value)


@validated_dataclass
class DocumentLink:
    id: str
    organization_id: str
    document_id: str
    module_code: str
    entity_type: str
    entity_id: str
    link_role: str = ""

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Document link ID is required.",
            code="DOCUMENT_LINK_ID_REQUIRED",
        )

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="DOCUMENT_LINK_ORGANIZATION_REQUIRED",
        )

    @field_validator("document_id", mode="before")
    @classmethod
    def _validate_document_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Document ID is required.",
            code="DOCUMENT_LINK_DOCUMENT_REQUIRED",
        )

    @field_validator("module_code", mode="before")
    @classmethod
    def _validate_module_code(cls, value: object) -> str:
        return normalize_document_module_code(value)

    @field_validator("entity_type", mode="before")
    @classmethod
    def _validate_entity_type(cls, value: object) -> str:
        return normalize_document_entity_type(value)

    @field_validator("entity_id", mode="before")
    @classmethod
    def _validate_entity_id(cls, value: object) -> str:
        return normalize_document_entity_id(value)

    @field_validator("link_role", mode="before")
    @classmethod
    def _normalize_link_role(cls, value: object) -> str:
        return normalize_document_link_role(value)

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
    "DocumentLink",
    "normalize_document_entity_id",
    "normalize_document_entity_type",
    "normalize_document_link_role",
    "normalize_document_module_code",
]
