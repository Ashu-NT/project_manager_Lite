from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class PartyType(str, Enum):
    GENERAL = "GENERAL"
    SUPPLIER = "SUPPLIER"
    MANUFACTURER = "MANUFACTURER"
    VENDOR = "VENDOR"
    CONTRACTOR = "CONTRACTOR"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"


def normalize_party_code(value: object) -> str:
    return normalize_required_text(
        value,
        message="Party code is required.",
        code="PARTY_CODE_REQUIRED",
    ).upper()


def normalize_party_name(value: object) -> str:
    return normalize_required_text(
        value,
        message="Party name is required.",
        code="PARTY_NAME_REQUIRED",
    )


def coerce_party_type(value: PartyType | str | None) -> PartyType:
    if isinstance(value, PartyType):
        return value
    raw = normalize_optional_text(value).upper() or PartyType.GENERAL.value
    try:
        return PartyType(raw)
    except ValueError as exc:
        raise ValidationError("Party type is invalid.", code="PARTY_TYPE_INVALID") from exc


def normalize_party_email(value: object) -> str:
    return normalize_optional_text(value).lower()


def normalize_party_phone(value: object) -> str:
    return normalize_optional_text(value)


@validated_dataclass
class Party:
    id: str
    organization_id: str
    party_code: str
    party_name: str
    party_type: PartyType = PartyType.GENERAL
    legal_name: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    website: str = ""
    tax_registration_number: str = ""
    external_reference: str = ""
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="PARTY_ORGANIZATION_REQUIRED",
        )

    @field_validator("party_code", mode="before")
    @classmethod
    def _validate_party_code(cls, value: object) -> str:
        return normalize_party_code(value)

    @field_validator("party_name", mode="before")
    @classmethod
    def _validate_party_name(cls, value: object) -> str:
        return normalize_party_name(value)

    @field_validator("party_type", mode="before")
    @classmethod
    def _validate_party_type(cls, value: PartyType | str | None) -> PartyType:
        return coerce_party_type(value)

    @field_validator(
        "legal_name",
        "contact_name",
        "country",
        "city",
        "address_line_1",
        "address_line_2",
        "postal_code",
        "website",
        "tax_registration_number",
        "external_reference",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str:
        return normalize_party_email(value)

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, value: object) -> str:
        return normalize_party_phone(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetimes(cls, value: object) -> datetime | None:
        if value in (None, ""):
            return None
        if not isinstance(value, datetime):
            raise ValidationError(
                "Party timestamps must be valid datetimes.",
                code="PARTY_TIMESTAMP_INVALID",
            )
        return value

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 1)
        if resolved < 1:
            raise ValidationError(
                "Party version must be positive.",
                code="PARTY_VERSION_INVALID",
            )
        return resolved

    @staticmethod
    def create(
        *,
        organization_id: str,
        party_code: str,
        party_name: str,
        party_type: PartyType | str = PartyType.GENERAL,
        legal_name: str = "",
        contact_name: str = "",
        email: str = "",
        phone: str = "",
        country: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        website: str = "",
        tax_registration_number: str = "",
        external_reference: str = "",
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Party":
        now = datetime.now(timezone.utc)
        return Party(
            id=generate_id(),
            organization_id=organization_id,
            party_code=party_code,
            party_name=party_name,
            party_type=party_type,
            legal_name=legal_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            country=country,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            website=website,
            tax_registration_number=tax_registration_number,
            external_reference=external_reference,
            is_active=is_active,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def name(self) -> str:
        return self.party_name

    @name.setter
    def name(self, value: str) -> None:
        self.party_name = value


__all__ = [
    "Party",
    "PartyType",
    "coerce_party_type",
    "normalize_party_code",
    "normalize_party_email",
    "normalize_party_name",
    "normalize_party_phone",
]
