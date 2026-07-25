from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from pydantic import field_validator, model_validator

from src.core.platform.common.ids import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def _validate_optional_datetime(value: object, *, code: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Site datetime values must be valid datetimes.",
            code=code,
        )
    return value


@validated_dataclass
class Site:
    id: str
    organization_id: str
    site_code: str
    name: str
    description: str = ""
    country: str = ""
    region: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    timezone: str = ""
    currency_code: str = ""
    site_type: str = ""
    status: str = "ACTIVE"
    default_calendar_id: str = ""
    default_language: str = ""
    is_active: bool = True
    opened_at: datetime | None = None
    closed_at: datetime | None = None
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
            code="SITE_ORGANIZATION_REQUIRED",
        )

    @field_validator("site_code", mode="before")
    @classmethod
    def _validate_site_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Site code is required.",
            code="SITE_CODE_REQUIRED",
        ).upper()

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Site name is required.",
            code="SITE_NAME_REQUIRED",
        )

    @field_validator(
        "description",
        "country",
        "region",
        "city",
        "address_line_1",
        "address_line_2",
        "postal_code",
        "timezone",
        "site_type",
        "status",
        "default_calendar_id",
        "default_language",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def _normalize_currency_code(cls, value: object) -> str:
        return normalize_optional_text(value).upper()

    @field_validator("opened_at", "closed_at", mode="before")
    @classmethod
    def _validate_window_datetimes(cls, value: object) -> datetime | None:
        return _validate_optional_datetime(value, code="SITE_DATETIME_INVALID")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_audit_datetimes(cls, value: object) -> datetime | None:
        return _validate_optional_datetime(value, code="SITE_TIMESTAMP_INVALID")

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 1)
        if resolved < 1:
            raise ValidationError(
                "Site version must be positive.",
                code="SITE_VERSION_INVALID",
            )
        return resolved

    @model_validator(mode="after")
    def _validate_site_state(self) -> "Site":
        if not self.status:
            object.__setattr__(self, "status", "ACTIVE" if self.is_active else "INACTIVE")
        else:
            object.__setattr__(self, "status", self.status.upper())
        if self.opened_at and self.closed_at and self.closed_at < self.opened_at:
            raise ValidationError(
                "Site closed date cannot be before opened date.",
                code="SITE_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        organization_id: str,
        site_code: str,
        name: str,
        *,
        description: str = "",
        country: str = "",
        region: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        timezone: str = "",
        currency_code: str = "",
        site_type: str = "",
        status: str = "ACTIVE",
        default_calendar_id: str = "",
        default_language: str = "",
        is_active: bool = True,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Site":
        now = datetime.now(dt_timezone.utc)
        return Site(
            id=generate_id(),
            organization_id=organization_id,
            site_code=site_code,
            name=name,
            description=description,
            country=country,
            region=region,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            timezone=timezone,
            currency_code=currency_code,
            site_type=site_type,
            status=status,
            default_calendar_id=default_calendar_id,
            default_language=default_language,
            is_active=is_active,
            opened_at=opened_at,
            closed_at=closed_at,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def display_name(self) -> str:
        return self.name

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name = value


__all__ = ["Site"]
