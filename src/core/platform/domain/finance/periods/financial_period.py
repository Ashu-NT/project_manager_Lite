"""Organization financial-period lifecycle and posting policy."""

from __future__ import annotations

import re
from dataclasses import field
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


_PERIOD_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")


class FinancialPeriodStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_optional_timestamp(value: object, *, code: str) -> datetime | None:
    if value in (None, ""):
        return None
    return _normalize_timestamp(value, code=code)


@validated_dataclass
class FinancialPeriod:
    """A posting period owned by one tenant organization.

    Closed and locked periods remain immutable. Reopening is deliberately not
    part of this aggregate until the product defines late-adjustment authority.
    """

    id: str
    tenant_id: str
    organization_id: str
    code: str
    name: str
    fiscal_year: int
    period_number: int
    start_date: date
    end_date: date
    created_by: str
    status: FinancialPeriodStatus = FinancialPeriodStatus.OPEN
    closed_by: str | None = None
    closed_at: datetime | None = None
    locked_by: str | None = None
    locked_at: datetime | None = None
    version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_by: str | None = None
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id",
        "tenant_id",
        "organization_id",
        "created_by",
        mode="before",
    )
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"{info.field_name.replace('_', ' ').title()} is required.",
            code=f"FINANCIAL_PERIOD_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Financial period code is required.",
            code="FINANCIAL_PERIOD_CODE_REQUIRED",
        ).upper()
        if not _PERIOD_CODE_PATTERN.fullmatch(normalized):
            raise ValidationError(
                "Financial period code must use 1-32 uppercase letters, numbers, dots, underscores, or hyphens.",
                code="FINANCIAL_PERIOD_CODE_INVALID",
            )
        return normalized

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Financial period name is required.",
            code="FINANCIAL_PERIOD_NAME_REQUIRED",
        )
        if len(normalized) > 128:
            raise ValidationError(
                "Financial period name cannot exceed 128 characters.",
                code="FINANCIAL_PERIOD_NAME_TOO_LONG",
            )
        return normalized

    @field_validator("updated_by", "closed_by", "locked_by", mode="before")
    @classmethod
    def _normalize_optional_actors(cls, value: object) -> str | None:
        return normalize_optional_text(value) or None

    @field_validator("fiscal_year", mode="before")
    @classmethod
    def _validate_fiscal_year(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Fiscal year must be a valid year.",
                code="FINANCIAL_PERIOD_FISCAL_YEAR_INVALID",
            ) from exc
        if normalized < 1 or normalized > 9999:
            raise ValidationError(
                "Fiscal year must be between 1 and 9999.",
                code="FINANCIAL_PERIOD_FISCAL_YEAR_INVALID",
            )
        return normalized

    @field_validator("period_number", mode="before")
    @classmethod
    def _validate_period_number(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Period number must be a positive integer.",
                code="FINANCIAL_PERIOD_NUMBER_INVALID",
            ) from exc
        if normalized < 1 or normalized > 999:
            raise ValidationError(
                "Period number must be between 1 and 999.",
                code="FINANCIAL_PERIOD_NUMBER_INVALID",
            )
        return normalized

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: object, info) -> date:
        if not isinstance(value, date) or isinstance(value, datetime):
            raise ValidationError(
                f"Financial period {info.field_name.replace('_', ' ')} must be a valid date.",
                code="FINANCIAL_PERIOD_DATE_INVALID",
            )
        return value

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Financial period version must be positive.",
                code="FINANCIAL_PERIOD_VERSION_INVALID",
            ) from exc
        if normalized < 1:
            raise ValidationError(
                "Financial period version must be positive.",
                code="FINANCIAL_PERIOD_VERSION_INVALID",
            )
        return normalized

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _normalize_timestamp(
            value,
            code=f"FINANCIAL_PERIOD_{info.field_name.upper()}_INVALID",
        )

    @field_validator("closed_at", "locked_at", mode="before")
    @classmethod
    def _validate_optional_timestamps(cls, value: object, info) -> datetime | None:
        return _normalize_optional_timestamp(
            value,
            code=f"FINANCIAL_PERIOD_{info.field_name.upper()}_INVALID",
        )

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "FinancialPeriod":
        if self.end_date < self.start_date:
            raise ValidationError(
                "Financial period end date cannot be before its start date.",
                code="FINANCIAL_PERIOD_DATE_RANGE_INVALID",
            )
        has_close = self.closed_by is not None and self.closed_at is not None
        has_lock = self.locked_by is not None and self.locked_at is not None
        if (self.closed_by is None) != (self.closed_at is None):
            raise ValidationError(
                "Financial period close actor and timestamp must be supplied together.",
                code="FINANCIAL_PERIOD_CLOSE_METADATA_INVALID",
            )
        if (self.locked_by is None) != (self.locked_at is None):
            raise ValidationError(
                "Financial period lock actor and timestamp must be supplied together.",
                code="FINANCIAL_PERIOD_LOCK_METADATA_INVALID",
            )
        if self.status == FinancialPeriodStatus.OPEN and (has_close or has_lock):
            raise ValidationError(
                "An open financial period cannot contain close or lock metadata.",
                code="FINANCIAL_PERIOD_OPEN_METADATA_INVALID",
            )
        if self.status == FinancialPeriodStatus.CLOSED and (not has_close or has_lock):
            raise ValidationError(
                "A closed financial period requires close metadata and cannot contain lock metadata.",
                code="FINANCIAL_PERIOD_CLOSED_METADATA_INVALID",
            )
        if self.status == FinancialPeriodStatus.LOCKED and (not has_close or not has_lock):
            raise ValidationError(
                "A locked financial period requires close and lock metadata.",
                code="FINANCIAL_PERIOD_LOCKED_METADATA_INVALID",
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        organization_id: str,
        code: str,
        name: str,
        fiscal_year: int,
        period_number: int,
        start_date: date,
        end_date: date,
        actor_id: str,
        now: datetime | None = None,
    ) -> "FinancialPeriod":
        timestamp = now or _utc_now()
        return cls(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            code=code,
            name=name,
            fiscal_year=fiscal_year,
            period_number=period_number,
            start_date=start_date,
            end_date=end_date,
            created_by=actor_id,
            created_at=timestamp,
            updated_by=actor_id,
            updated_at=timestamp,
        )

    def contains(self, posting_date: date) -> bool:
        return self.start_date <= posting_date <= self.end_date

    @property
    def accepts_normal_posting(self) -> bool:
        return self.status == FinancialPeriodStatus.OPEN

    def require_normal_posting(self) -> None:
        if not self.accepts_normal_posting:
            raise BusinessRuleError(
                f"Financial period '{self.code}' is {self.status.value} and rejects normal posting.",
                code="FINANCIAL_PERIOD_POSTING_BLOCKED",
            )

    def update_definition(
        self,
        *,
        actor_id: str,
        now: datetime,
        code: str | None = None,
        name: str | None = None,
        fiscal_year: int | None = None,
        period_number: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> None:
        if self.status != FinancialPeriodStatus.OPEN:
            raise BusinessRuleError(
                "Only an open financial period can be edited.",
                code="FINANCIAL_PERIOD_NOT_EDITABLE",
            )
        candidate = FinancialPeriod(
            **{
                **self.__dict__,
                "code": self.code if code is None else code,
                "name": self.name if name is None else name,
                "fiscal_year": self.fiscal_year if fiscal_year is None else fiscal_year,
                "period_number": self.period_number if period_number is None else period_number,
                "start_date": self.start_date if start_date is None else start_date,
                "end_date": self.end_date if end_date is None else end_date,
                "updated_by": actor_id,
                "updated_at": now,
            }
        )
        self._apply_validated_candidate(
            candidate,
            "code",
            "name",
            "fiscal_year",
            "period_number",
            "start_date",
            "end_date",
            "updated_by",
            "updated_at",
        )

    def close(self, *, actor_id: str, now: datetime) -> None:
        if self.status != FinancialPeriodStatus.OPEN:
            raise BusinessRuleError(
                "Only an open financial period can be closed.",
                code="FINANCIAL_PERIOD_CLOSE_INVALID",
            )
        candidate = FinancialPeriod(
            **{
                **self.__dict__,
                "status": FinancialPeriodStatus.CLOSED,
                "closed_by": actor_id,
                "closed_at": now,
                "updated_by": actor_id,
                "updated_at": now,
            }
        )
        self._apply_validated_candidate(
            candidate,
            "status",
            "closed_by",
            "closed_at",
            "updated_by",
            "updated_at",
        )

    def lock(self, *, actor_id: str, now: datetime) -> None:
        if self.status != FinancialPeriodStatus.CLOSED:
            raise BusinessRuleError(
                "Only a closed financial period can be locked.",
                code="FINANCIAL_PERIOD_LOCK_INVALID",
            )
        candidate = FinancialPeriod(
            **{
                **self.__dict__,
                "status": FinancialPeriodStatus.LOCKED,
                "locked_by": actor_id,
                "locked_at": now,
                "updated_by": actor_id,
                "updated_at": now,
            }
        )
        self._apply_validated_candidate(
            candidate,
            "status",
            "locked_by",
            "locked_at",
            "updated_by",
            "updated_at",
        )

    def _apply_validated_candidate(
        self,
        candidate: "FinancialPeriod",
        *field_names: str,
    ) -> None:
        # Pydantic validates assignments one field at a time. Applying a
        # complete pre-validated state avoids transient lifecycle/range errors.
        for field_name in field_names:
            object.__setattr__(self, field_name, getattr(candidate, field_name))


__all__ = ["FinancialPeriod", "FinancialPeriodStatus"]
