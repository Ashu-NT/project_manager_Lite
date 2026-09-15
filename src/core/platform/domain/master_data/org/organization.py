from __future__ import annotations

from pydantic import field_validator

from src.core.platform.common.ids import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.domain.master_data.org.support import (
    normalize_country_code,
    normalize_email,
    normalize_optional_organization_text,
    normalize_phone,
)
from src.core.platform.finance.money.currency import CurrencyCode

_OPTIONAL_TEXT_FIELDS = (
    "legal_name",
    "registration_number",
    "tax_id",
    "address_line_1",
    "address_line_2",
    "postal_code",
    "city",
    "state_region",
    "website",
)


@validated_dataclass
class Organization:
    id: str
    organization_code: str
    display_name: str
    timezone_name: str = "UTC"
    base_currency: str = "EUR"
    is_enabled: bool = True
    version: int = 1
    tenant_id: str | None = None
    # Legal identity
    legal_name: str = ""
    registration_number: str = ""
    tax_id: str = ""
    # Registered address
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    city: str = ""
    state_region: str = ""
    country_code: str = ""
    # Primary contact
    email: str = ""
    phone: str = ""
    website: str = ""

    @field_validator("organization_code", mode="before")
    @classmethod
    def _validate_organization_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization code is required.",
            code="ORGANIZATION_CODE_REQUIRED",
        ).upper()

    @field_validator("display_name", mode="before")
    @classmethod
    def _validate_display_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization name is required.",
            code="ORGANIZATION_NAME_REQUIRED",
        )

    @field_validator("timezone_name", mode="before")
    @classmethod
    def _validate_timezone_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Timezone is required.",
            code="TIMEZONE_REQUIRED",
        )

    @field_validator("base_currency", mode="before")
    @classmethod
    def _validate_base_currency(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Base currency is required.",
            code="BASE_CURRENCY_REQUIRED",
        ).upper()
        try:
            currency = CurrencyCode(normalized)
            currency.minor_unit_quantum()
        except ValidationError as exc:
            raise ValidationError(
                "Base currency must be an active ISO 4217 currency with defined minor units.",
                code="BASE_CURRENCY_INVALID",
            ) from exc
        return currency.code

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _normalize_tenant_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator(*_OPTIONAL_TEXT_FIELDS, mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str:
        return normalize_optional_organization_text(value)

    @field_validator("country_code", mode="before")
    @classmethod
    def _normalize_country_code(cls, value: object) -> str:
        return normalize_country_code(value)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str:
        return normalize_email(value)

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, value: object) -> str:
        return normalize_phone(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 1)
        if resolved < 1:
            raise ValidationError(
                "Organization version must be positive.",
                code="ORGANIZATION_VERSION_INVALID",
            )
        return resolved

    @staticmethod
    def create(
        organization_code: str,
        display_name: str,
        timezone_name: str = "UTC",
        base_currency: str = "EUR",
        is_enabled: bool = True,
        tenant_id: str | None = None,
        legal_name: str = "",
        registration_number: str = "",
        tax_id: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        city: str = "",
        state_region: str = "",
        country_code: str = "",
        email: str = "",
        phone: str = "",
        website: str = "",
    ) -> "Organization":
        return Organization(
            id=generate_id(),
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_enabled=is_enabled,
            version=1,
            tenant_id=tenant_id,
            legal_name=legal_name,
            registration_number=registration_number,
            tax_id=tax_id,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            city=city,
            state_region=state_region,
            country_code=country_code,
            email=email,
            phone=phone,
            website=website,
        )


__all__ = ["Organization"]
