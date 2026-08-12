from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.financials.forecast import (
    ForecastLine,
    ForecastSourceDecision,
    ProjectForecast,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


@validated_dataclass(frozen=True)
class ManualEtcEstimate:
    cost_code_id: str
    amount: Decimal
    description: str
    task_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None

    @field_validator("cost_code_id", mode="before")
    @classmethod
    def _cost_code_required(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Manual ETC cost code is required.",
            code="PROJECT_FORECAST_MANUAL_COST_CODE_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", mode="before")
    @classmethod
    def _description_required(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Manual ETC description is required.",
            code="PROJECT_FORECAST_MANUAL_DESCRIPTION_REQUIRED",
        )

    @field_validator("amount", mode="before")
    @classmethod
    def _amount_nonnegative(cls, value: object) -> Decimal:
        resolved = Decimal(str(value))
        if resolved < 0:
            raise ValidationError(
                "Manual ETC amount cannot be negative.",
                code="PROJECT_FORECAST_MANUAL_AMOUNT_INVALID",
            )
        return resolved

    @model_validator(mode="after")
    def _period_valid(self) -> "ManualEtcEstimate":
        _validate_period(self.period_start, self.period_end)
        return self


@validated_dataclass(frozen=True)
class RiskContingencyEstimate:
    risk_id: str
    cost_code_id: str
    amount: Decimal
    description: str = ""
    task_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None

    @field_validator("risk_id", "cost_code_id", mode="before")
    @classmethod
    def _identifier_required(cls, value: object, info) -> str:
        return normalize_required_text(
            value,
            message=f"Risk contingency {info.field_name.replace('_', ' ')} is required.",
            code=f"PROJECT_FORECAST_RISK_{info.field_name.upper()}_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("amount", mode="before")
    @classmethod
    def _amount_nonnegative(cls, value: object) -> Decimal:
        resolved = Decimal(str(value))
        if resolved < 0:
            raise ValidationError(
                "Risk contingency amount cannot be negative.",
                code="PROJECT_FORECAST_RISK_AMOUNT_INVALID",
            )
        return resolved

    @model_validator(mode="after")
    def _period_valid(self) -> "RiskContingencyEstimate":
        _validate_period(self.period_start, self.period_end)
        return self


def _validate_period(start: date | None, end: date | None) -> None:
    if (start is None) != (end is None):
        raise ValidationError(
            "Forecast period start and end must be provided together.",
            code="PROJECT_FORECAST_GENERATION_PERIOD_INCOMPLETE",
        )
    if start and end and end < start:
        raise ValidationError(
            "Forecast period end cannot precede period start.",
            code="PROJECT_FORECAST_GENERATION_PERIOD_INVALID",
        )


@dataclass(frozen=True, slots=True)
class ForecastGenerationResult:
    forecast: ProjectForecast
    lines: tuple[ForecastLine, ...]
    decisions: tuple[ForecastSourceDecision, ...]
    planned_total: Decimal
    posted_actual_offset: Decimal
    open_commitment_total: Decimal
    remaining_plan_total: Decimal
    manual_etc_total: Decimal
    risk_contingency_total: Decimal
    etc_total: Decimal


__all__ = [
    "ForecastGenerationResult",
    "ManualEtcEstimate",
    "RiskContingencyEstimate",
]
