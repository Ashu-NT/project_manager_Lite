from __future__ import annotations

from datetime import date, datetime, timezone
from dataclasses import field
from decimal import Decimal
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.domain.portfolio.validation import (
    _DEFAULT_SCORING_TEMPLATE_NAME,
    _validate_non_negative_decimal,
    _validate_non_negative_float,
    _validate_portfolio_date,
    _validate_portfolio_datetime,
    _validate_portfolio_score,
    _validate_portfolio_weight,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class PortfolioIntakeStatus(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"


def as_portfolio_intake_status(value: PortfolioIntakeStatus | str) -> PortfolioIntakeStatus:
    if isinstance(value, PortfolioIntakeStatus):
        return value
    raw = normalize_optional_text(value).upper() or PortfolioIntakeStatus.PROPOSED.value
    try:
        return PortfolioIntakeStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Portfolio intake status is invalid.",
            code="PORTFOLIO_INTAKE_STATUS_INVALID",
        ) from exc


def calculate_portfolio_intake_composite_score(
    *,
    strategic_score: int,
    value_score: int,
    urgency_score: int,
    risk_score: int,
    strategic_weight: int,
    value_weight: int,
    urgency_weight: int,
    risk_weight: int,
) -> int:
    return (
        int(strategic_score or 0) * int(strategic_weight or 0)
        + int(value_score or 0) * int(value_weight or 0)
        + int(urgency_score or 0) * int(urgency_weight or 0)
        - int(risk_score or 0) * int(risk_weight or 0)
    )


@validated_dataclass
class PortfolioIntakeItem:
    id: str
    title: str
    sponsor_name: str
    organization_id: str = ""
    summary: str = ""
    requested_budget: Decimal = Decimal("0")
    requested_capacity_percent: float = 0.0
    target_start_date: date | None = None
    strategic_score: int = 3
    value_score: int = 3
    urgency_score: int = 3
    risk_score: int = 3
    scoring_template_id: str = ""
    scoring_template_name: str = "Balanced PMO"
    strategic_weight: int = 3
    value_weight: int = 2
    urgency_weight: int = 2
    risk_weight: int = 1
    status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="PORTFOLIO_INTAKE_ORGANIZATION_REQUIRED",
        )

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Portfolio intake title is required.",
            code="PORTFOLIO_INTAKE_TITLE_REQUIRED",
        )

    @field_validator("sponsor_name", mode="before")
    @classmethod
    def _validate_sponsor_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Portfolio intake sponsor is required.",
            code="PORTFOLIO_INTAKE_SPONSOR_REQUIRED",
        )

    @field_validator("summary", "scoring_template_id", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("scoring_template_name", mode="before")
    @classmethod
    def _normalize_template_name(cls, value: object) -> str:
        normalized = normalize_optional_text(value)
        return normalized or _DEFAULT_SCORING_TEMPLATE_NAME

    @field_validator("requested_budget", mode="before")
    @classmethod
    def _validate_requested_budget(cls, value: object) -> Decimal:
        return _validate_non_negative_decimal(
            value,
            label="Requested budget",
            code="PORTFOLIO_INTAKE_BUDGET_INVALID",
        )

    @field_validator("requested_capacity_percent", mode="before")
    @classmethod
    def _validate_requested_capacity_percent(cls, value: object) -> float:
        return _validate_non_negative_float(
            value,
            label="Requested capacity",
            code="PORTFOLIO_INTAKE_CAPACITY_INVALID",
        )

    @field_validator("target_start_date", mode="before")
    @classmethod
    def _validate_target_start_date(cls, value: object) -> date | None:
        return _validate_portfolio_date(
            value,
            message="Portfolio intake target start date must be a valid date.",
            code="PORTFOLIO_INTAKE_TARGET_START_INVALID",
        )

    @field_validator("strategic_score", mode="before")
    @classmethod
    def _validate_strategic_score(cls, value: object) -> int:
        return _validate_portfolio_score(
            value,
            label="Strategic score",
            code="PORTFOLIO_INTAKE_STRATEGIC_SCORE_INVALID",
        )

    @field_validator("value_score", mode="before")
    @classmethod
    def _validate_value_score(cls, value: object) -> int:
        return _validate_portfolio_score(
            value,
            label="Value score",
            code="PORTFOLIO_INTAKE_VALUE_SCORE_INVALID",
        )

    @field_validator("urgency_score", mode="before")
    @classmethod
    def _validate_urgency_score(cls, value: object) -> int:
        return _validate_portfolio_score(
            value,
            label="Urgency score",
            code="PORTFOLIO_INTAKE_URGENCY_SCORE_INVALID",
        )

    @field_validator("risk_score", mode="before")
    @classmethod
    def _validate_risk_score(cls, value: object) -> int:
        return _validate_portfolio_score(
            value,
            label="Risk score",
            code="PORTFOLIO_INTAKE_RISK_SCORE_INVALID",
        )

    @field_validator("strategic_weight", mode="before")
    @classmethod
    def _validate_strategic_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Strategic weight",
            code="PORTFOLIO_INTAKE_STRATEGIC_WEIGHT_INVALID",
        )

    @field_validator("value_weight", mode="before")
    @classmethod
    def _validate_value_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Value weight",
            code="PORTFOLIO_INTAKE_VALUE_WEIGHT_INVALID",
        )

    @field_validator("urgency_weight", mode="before")
    @classmethod
    def _validate_urgency_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Urgency weight",
            code="PORTFOLIO_INTAKE_URGENCY_WEIGHT_INVALID",
        )

    @field_validator("risk_weight", mode="before")
    @classmethod
    def _validate_risk_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Risk weight",
            code="PORTFOLIO_INTAKE_RISK_WEIGHT_INVALID",
        )

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> PortfolioIntakeStatus:
        return as_portfolio_intake_status(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime:
        return _validate_portfolio_datetime(
            value,
            message="Portfolio intake timestamps must be valid datetimes.",
            code="PORTFOLIO_INTAKE_TIMESTAMP_INVALID",
        )

    @model_validator(mode="after")
    def _validate_weight_mix(self) -> "PortfolioIntakeItem":
        if (self.strategic_weight + self.value_weight + self.urgency_weight) <= 0:
            raise ValidationError(
                "At least one positive delivery weight is required.",
                code="PORTFOLIO_TEMPLATE_EMPTY",
            )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        title: str,
        sponsor_name: str,
        summary: str = "",
        requested_budget: Decimal | int | str = Decimal("0"),
        requested_capacity_percent: float = 0.0,
        target_start_date: date | None = None,
        strategic_score: int = 3,
        value_score: int = 3,
        urgency_score: int = 3,
        risk_score: int = 3,
        scoring_template_id: str = "",
        scoring_template_name: str = "Balanced PMO",
        strategic_weight: int = 3,
        value_weight: int = 2,
        urgency_weight: int = 2,
        risk_weight: int = 1,
        status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED,
    ) -> "PortfolioIntakeItem":
        now = datetime.now(timezone.utc)
        return PortfolioIntakeItem(
            id=generate_id(),
            organization_id=organization_id,
            title=title,
            sponsor_name=sponsor_name,
            summary=summary,
            requested_budget=requested_budget,
            requested_capacity_percent=requested_capacity_percent,
            target_start_date=target_start_date,
            strategic_score=strategic_score,
            value_score=value_score,
            urgency_score=urgency_score,
            risk_score=risk_score,
            scoring_template_id=scoring_template_id,
            scoring_template_name=scoring_template_name,
            strategic_weight=strategic_weight,
            value_weight=value_weight,
            urgency_weight=urgency_weight,
            risk_weight=risk_weight,
            status=status,
            created_at=now,
            updated_at=now,
            version=1,
        )

    @property
    def composite_score(self) -> int:
        return calculate_portfolio_intake_composite_score(
            strategic_score=self.strategic_score,
            value_score=self.value_score,
            urgency_score=self.urgency_score,
            risk_score=self.risk_score,
            strategic_weight=self.strategic_weight,
            value_weight=self.value_weight,
            urgency_weight=self.urgency_weight,
            risk_weight=self.risk_weight,
        )


__all__ = [
    "PortfolioIntakeItem",
    "PortfolioIntakeStatus",
    "as_portfolio_intake_status",
    "calculate_portfolio_intake_composite_score",
]
