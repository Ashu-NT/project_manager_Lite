from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.domain.portfolio.validation import (
    _validate_portfolio_datetime,
    _validate_portfolio_weight,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


@validated_dataclass
class PortfolioScoringTemplate:
    id: str
    name: str
    organization_id: str = ""
    summary: str = ""
    strategic_weight: int = 3
    value_weight: int = 2
    urgency_weight: int = 2
    risk_weight: int = 1
    is_active: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="PORTFOLIO_TEMPLATE_ORGANIZATION_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Scoring template name is required.",
            code="PORTFOLIO_TEMPLATE_NAME_REQUIRED",
        )

    @field_validator("summary", mode="before")
    @classmethod
    def _normalize_summary(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("strategic_weight", mode="before")
    @classmethod
    def _validate_strategic_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Strategic weight",
            code="PORTFOLIO_TEMPLATE_STRATEGIC_WEIGHT_INVALID",
        )

    @field_validator("value_weight", mode="before")
    @classmethod
    def _validate_value_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Value weight",
            code="PORTFOLIO_TEMPLATE_VALUE_WEIGHT_INVALID",
        )

    @field_validator("urgency_weight", mode="before")
    @classmethod
    def _validate_urgency_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Urgency weight",
            code="PORTFOLIO_TEMPLATE_URGENCY_WEIGHT_INVALID",
        )

    @field_validator("risk_weight", mode="before")
    @classmethod
    def _validate_risk_weight(cls, value: object) -> int:
        return _validate_portfolio_weight(
            value,
            label="Risk weight",
            code="PORTFOLIO_TEMPLATE_RISK_WEIGHT_INVALID",
        )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime:
        return _validate_portfolio_datetime(
            value,
            message="Portfolio scoring template timestamps must be valid datetimes.",
            code="PORTFOLIO_TEMPLATE_TIMESTAMP_INVALID",
        )

    @model_validator(mode="after")
    def _validate_weight_mix(self) -> "PortfolioScoringTemplate":
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
        name: str,
        summary: str = "",
        strategic_weight: int = 3,
        value_weight: int = 2,
        urgency_weight: int = 2,
        risk_weight: int = 1,
        is_active: bool = False,
    ) -> "PortfolioScoringTemplate":
        now = datetime.now(timezone.utc)
        return PortfolioScoringTemplate(
            id=generate_id(),
            organization_id=organization_id,
            name=name,
            summary=summary,
            strategic_weight=strategic_weight,
            value_weight=value_weight,
            urgency_weight=urgency_weight,
            risk_weight=risk_weight,
            is_active=bool(is_active),
            created_at=now,
            updated_at=now,
        )

    @property
    def weight_summary(self) -> str:
        return (
            f"Strategic x{int(self.strategic_weight or 0)}, "
            f"Value x{int(self.value_weight or 0)}, "
            f"Urgency x{int(self.urgency_weight or 0)}, "
            f"Risk x{int(self.risk_weight or 0)}"
        )


__all__ = ["PortfolioScoringTemplate"]
