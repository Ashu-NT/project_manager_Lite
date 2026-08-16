from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.domain.portfolio.validation import (
    _validate_portfolio_datetime,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


@validated_dataclass
class PortfolioProjectDependency:
    id: str
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Portfolio dependency ID is required.",
            code="PORTFOLIO_DEPENDENCY_ID_REQUIRED",
        )

    @field_validator("predecessor_project_id", mode="before")
    @classmethod
    def _validate_predecessor_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Predecessor project ID is required.",
            code="PORTFOLIO_DEPENDENCY_PREDECESSOR_REQUIRED",
        )

    @field_validator("successor_project_id", mode="before")
    @classmethod
    def _validate_successor_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Successor project ID is required.",
            code="PORTFOLIO_DEPENDENCY_SUCCESSOR_REQUIRED",
        )

    @field_validator("dependency_type", mode="before")
    @classmethod
    def _validate_dependency_type(cls, value: object) -> DependencyType:
        if isinstance(value, DependencyType):
            return value
        raw = normalize_optional_text(value).upper() or DependencyType.FINISH_TO_START.value
        try:
            return DependencyType(raw)
        except ValueError as exc:
            raise ValidationError(
                "Portfolio dependency type is invalid.",
                code="PORTFOLIO_DEPENDENCY_TYPE_INVALID",
            ) from exc

    @field_validator("summary", mode="before")
    @classmethod
    def _normalize_summary(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime:
        return _validate_portfolio_datetime(
            value,
            message="Portfolio dependency timestamps must be valid datetimes.",
            code="PORTFOLIO_DEPENDENCY_TIMESTAMP_INVALID",
        )

    @model_validator(mode="after")
    def _validate_project_pair(self) -> "PortfolioProjectDependency":
        if self.predecessor_project_id == self.successor_project_id:
            raise ValidationError(
                "Portfolio dependency must link two different projects.",
                code="PORTFOLIO_DEPENDENCY_SAME_PROJECT",
            )
        return self

    @staticmethod
    def create(
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType | str = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> "PortfolioProjectDependency":
        now = datetime.now(timezone.utc)
        return PortfolioProjectDependency(
            id=generate_id(),
            predecessor_project_id=predecessor_project_id,
            successor_project_id=successor_project_id,
            dependency_type=dependency_type,
            summary=summary,
            created_at=now,
            updated_at=now,
        )


@dataclass
class PortfolioProjectDependencyView:
    dependency_id: str
    predecessor_project_id: str
    predecessor_project_name: str
    predecessor_project_status: str
    successor_project_id: str
    successor_project_name: str
    successor_project_status: str
    dependency_type: DependencyType
    summary: str
    pressure_label: str
    created_at: datetime


__all__ = ["PortfolioProjectDependency", "PortfolioProjectDependencyView"]
