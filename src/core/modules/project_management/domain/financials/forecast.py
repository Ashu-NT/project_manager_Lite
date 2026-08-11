from __future__ import annotations

from dataclasses import field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance.money.currency import CurrencyCode
from src.core.platform.finance.money.money import Money


class ForecastStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ForecastGenerationMode(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    HYBRID = "hybrid"


class ForecastLineSourceKind(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class ForecastLineSourceType(str, Enum):
    REMAINING_PLAN = "remaining_plan"
    OPEN_COMMITMENT = "open_commitment"
    RISK = "risk"
    MANUAL_ESTIMATE = "manual_estimate"


_ALLOWED_TRANSITIONS: dict[ForecastStatus, frozenset[ForecastStatus]] = {
    ForecastStatus.DRAFT: frozenset({ForecastStatus.SUBMITTED}),
    ForecastStatus.SUBMITTED: frozenset(
        {ForecastStatus.APPROVED, ForecastStatus.REJECTED}
    ),
    ForecastStatus.APPROVED: frozenset({ForecastStatus.SUPERSEDED}),
    ForecastStatus.REJECTED: frozenset(),
    ForecastStatus.SUPERSEDED: frozenset(),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_identifier(value: object, *, label: str, code: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=code,
    )


@validated_dataclass
class ProjectForecast:
    """A reproducible, versioned ETC snapshot for one project."""

    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    name: str
    currency_code: str
    as_of_date: date
    generation_mode: ForecastGenerationMode
    created_by: str
    status: ForecastStatus = ForecastStatus.DRAFT
    revision: int = 1
    row_version: int = 1
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    superseded_by: str | None = None
    superseded_at: datetime | None = None
    notes: str = ""
    submission_notes: str = ""
    approval_notes: str = ""
    rejection_notes: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "created_by",
        mode="before",
    )
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PROJECT_FORECAST_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Forecast name is required.",
            code="PROJECT_FORECAST_NAME_REQUIRED",
        )

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator(
        "submitted_by", "approved_by", "rejected_by", "superseded_by",
        mode="before",
    )
    @classmethod
    def _normalize_optional_actor(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("revision", "row_version", mode="before")
    @classmethod
    def _validate_positive_int(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                f"Forecast {info.field_name.replace('_', ' ')} must be positive.",
                code=f"PROJECT_FORECAST_{info.field_name.upper()}_INVALID",
            )
        return resolved

    @field_validator(
        "submitted_at", "approved_at", "rejected_at", "superseded_at",
        mode="before",
    )
    @classmethod
    def _validate_optional_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _timestamp(value, code=f"PROJECT_FORECAST_{info.field_name.upper()}_INVALID")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"PROJECT_FORECAST_{info.field_name.upper()}_INVALID")

    @property
    def is_mutable(self) -> bool:
        return self.status == ForecastStatus.DRAFT

    def ensure_mutable(self) -> None:
        if not self.is_mutable:
            raise BusinessRuleError(
                f"Forecast cannot be modified in status '{self.status.value}'.",
                code="PROJECT_FORECAST_IMMUTABLE",
            )

    def touch(self, *, updated_at: datetime) -> None:
        self.updated_at = updated_at

    def _transition(self, target: ForecastStatus, *, code: str) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise BusinessRuleError(
                f"Forecast cannot transition from {self.status.value} to {target.value}.",
                code=code,
            )
        self.status = target

    def submit(self, *, submitted_by: str, submitted_at: datetime, notes: str = "") -> None:
        self._transition(ForecastStatus.SUBMITTED, code="PROJECT_FORECAST_SUBMIT_STATUS_INVALID")
        self.submitted_by = submitted_by
        self.submitted_at = submitted_at
        self.submission_notes = notes
        self.updated_at = submitted_at

    def approve(self, *, approved_by: str, approved_at: datetime, notes: str = "") -> None:
        self._transition(ForecastStatus.APPROVED, code="PROJECT_FORECAST_APPROVE_STATUS_INVALID")
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.approval_notes = notes
        self.updated_at = approved_at

    def reject(self, *, rejected_by: str, rejected_at: datetime, notes: str = "") -> None:
        self._transition(ForecastStatus.REJECTED, code="PROJECT_FORECAST_REJECT_STATUS_INVALID")
        self.rejected_by = rejected_by
        self.rejected_at = rejected_at
        self.rejection_notes = notes
        self.updated_at = rejected_at

    def supersede(self, *, superseded_by: str, superseded_at: datetime) -> None:
        self._transition(
            ForecastStatus.SUPERSEDED,
            code="PROJECT_FORECAST_SUPERSEDE_STATUS_INVALID",
        )
        self.superseded_by = superseded_by
        self.superseded_at = superseded_at
        self.updated_at = superseded_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        name: str,
        currency_code: str,
        as_of_date: date,
        generation_mode: ForecastGenerationMode,
        created_by: str,
        revision: int = 1,
        created_at: datetime | None = None,
        **values,
    ) -> "ProjectForecast":
        now = created_at or _utc_now()
        return ProjectForecast(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            name=name,
            currency_code=currency_code,
            as_of_date=as_of_date,
            generation_mode=generation_mode,
            created_by=created_by,
            revision=revision,
            created_at=now,
            updated_at=now,
            **values,
        )


@validated_dataclass
class ForecastLine:
    id: str
    tenant_id: str
    organization_id: str
    forecast_id: str
    project_id: str
    cost_code_id: str
    description: str
    amount: Decimal
    currency_code: str
    source_kind: ForecastLineSourceKind
    source_type: ForecastLineSourceType
    created_by: str
    task_id: str | None = None
    source_reference_type: str | None = None
    source_reference_id: str | None = None
    source_snapshot_at: datetime | None = None
    period_start: date | None = None
    period_end: date | None = None
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "forecast_id", "project_id",
        "cost_code_id", "created_by", mode="before",
    )
    @classmethod
    def _validate_identifiers(cls, value: object, info) -> str:
        return _required_identifier(
            value,
            label=info.field_name.replace("_", " ").title(),
            code=f"PROJECT_FORECAST_LINE_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("task_id", "source_reference_id", mode="before")
    @classmethod
    def _normalize_optional_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("source_reference_type", mode="before")
    @classmethod
    def _normalize_source_reference_type(cls, value: object) -> str | None:
        if value in (None, ""):
            return None
        return normalize_required_text(
            value,
            message="Source reference type is invalid.",
            code="PROJECT_FORECAST_LINE_SOURCE_REFERENCE_TYPE_INVALID",
        ).lower()

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("amount", mode="before")
    @classmethod
    def _validate_amount(cls, value: object) -> Decimal:
        resolved = Decimal(str(value if value not in (None, "") else "0"))
        if resolved < 0:
            raise ValidationError(
                "Forecast line amount cannot be negative.",
                code="PROJECT_FORECAST_LINE_AMOUNT_INVALID",
            )
        return resolved

    @field_validator("source_snapshot_at", mode="before")
    @classmethod
    def _validate_snapshot_at(cls, value: object) -> datetime | None:
        if value is None:
            return None
        return _timestamp(value, code="PROJECT_FORECAST_LINE_SOURCE_SNAPSHOT_INVALID")

    @field_validator("row_version", mode="before")
    @classmethod
    def _validate_row_version(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                "Forecast line row version must be positive.",
                code="PROJECT_FORECAST_LINE_ROW_VERSION_INVALID",
            )
        return resolved

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"PROJECT_FORECAST_LINE_{info.field_name.upper()}_INVALID")

    @model_validator(mode="after")
    def _validate_source_and_period(self) -> "ForecastLine":
        manual = self.source_kind == ForecastLineSourceKind.MANUAL
        if manual != (self.source_type == ForecastLineSourceType.MANUAL_ESTIMATE):
            raise ValidationError(
                "Manual forecast lines must use the manual-estimate source type.",
                code="PROJECT_FORECAST_LINE_SOURCE_MISMATCH",
            )
        if self.source_kind == ForecastLineSourceKind.AUTOMATIC:
            if not self.source_reference_type or not self.source_reference_id:
                raise ValidationError(
                    "Automatic forecast lines require a source reference.",
                    code="PROJECT_FORECAST_LINE_SOURCE_REFERENCE_REQUIRED",
                )
            if self.source_snapshot_at is None:
                raise ValidationError(
                    "Automatic forecast lines require a source snapshot timestamp.",
                    code="PROJECT_FORECAST_LINE_SOURCE_SNAPSHOT_REQUIRED",
                )
        if (self.period_start is None) != (self.period_end is None):
            raise ValidationError(
                "Forecast line period start and end must be provided together.",
                code="PROJECT_FORECAST_LINE_PERIOD_INCOMPLETE",
            )
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValidationError(
                "Forecast line period end cannot precede period start.",
                code="PROJECT_FORECAST_LINE_PERIOD_INVALID",
            )
        return self

    @property
    def money(self) -> Money:
        return Money.of(self.amount, self.currency_code)

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        forecast_id: str,
        project_id: str,
        cost_code_id: str,
        description: str,
        amount: Decimal,
        currency_code: str,
        source_kind: ForecastLineSourceKind,
        source_type: ForecastLineSourceType,
        created_by: str,
        created_at: datetime | None = None,
        **values,
    ) -> "ForecastLine":
        now = created_at or _utc_now()
        return ForecastLine(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            forecast_id=forecast_id,
            project_id=project_id,
            cost_code_id=cost_code_id,
            description=description,
            amount=amount,
            currency_code=currency_code,
            source_kind=source_kind,
            source_type=source_type,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            **values,
        )


__all__ = [
    "ForecastGenerationMode",
    "ForecastLine",
    "ForecastLineSourceKind",
    "ForecastLineSourceType",
    "ForecastStatus",
    "ProjectForecast",
]
