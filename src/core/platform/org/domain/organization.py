from __future__ import annotations

from pydantic import field_validator

from src.core.platform.common.ids import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode


@validated_dataclass
class Organization:
    id: str
    organization_code: str
    display_name: str
    timezone_name: str = "UTC"
    base_currency: str = "EUR"
    is_active: bool = True
    version: int = 1
    tenant_id: str | None = None

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
        is_active: bool = True,
        tenant_id: str | None = None,
    ) -> "Organization":
        return Organization(
            id=generate_id(),
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=is_active,
            version=1,
            tenant_id=tenant_id,
        )


__all__ = ["Organization"]
