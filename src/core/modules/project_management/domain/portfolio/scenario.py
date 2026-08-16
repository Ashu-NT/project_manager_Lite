from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from pydantic import field_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.domain.portfolio.validation import (
    _normalize_identifier_list,
    _validate_optional_non_negative_decimal,
    _validate_optional_non_negative_float,
    _validate_portfolio_datetime,
)
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


@validated_dataclass
class PortfolioScenario:
    id: str
    name: str
    organization_id: str = ""
    budget_limit: Decimal | None = None
    capacity_limit_percent: float | None = None
    project_ids: list[str] = field(default_factory=list)
    intake_item_ids: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="PORTFOLIO_SCENARIO_ORGANIZATION_REQUIRED",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Portfolio scenario name is required.",
            code="PORTFOLIO_SCENARIO_NAME_REQUIRED",
        )

    @field_validator("budget_limit", mode="before")
    @classmethod
    def _validate_budget_limit(cls, value: object) -> Decimal | None:
        return _validate_optional_non_negative_decimal(
            value,
            label="Budget limit",
            code="PORTFOLIO_SCENARIO_BUDGET_INVALID",
        )

    @field_validator("capacity_limit_percent", mode="before")
    @classmethod
    def _validate_capacity_limit_percent(cls, value: object) -> float | None:
        return _validate_optional_non_negative_float(
            value,
            label="Capacity limit",
            code="PORTFOLIO_SCENARIO_CAPACITY_INVALID",
        )

    @field_validator("project_ids", "intake_item_ids", mode="before")
    @classmethod
    def _normalize_identifier_collections(cls, value: object) -> list[str]:
        return _normalize_identifier_list(value)

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime:
        return _validate_portfolio_datetime(
            value,
            message="Portfolio scenario timestamps must be valid datetimes.",
            code="PORTFOLIO_SCENARIO_TIMESTAMP_INVALID",
        )

    @staticmethod
    def create(
        *,
        organization_id: str,
        name: str,
        budget_limit: Decimal | int | str | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: Iterable[str] | None = None,
        intake_item_ids: Iterable[str] | None = None,
        notes: str = "",
    ) -> "PortfolioScenario":
        now = datetime.now(timezone.utc)
        return PortfolioScenario(
            id=generate_id(),
            organization_id=organization_id,
            name=name,
            budget_limit=budget_limit,
            capacity_limit_percent=capacity_limit_percent,
            project_ids=list(project_ids or []),
            intake_item_ids=list(intake_item_ids or []),
            notes=notes,
            created_at=now,
            updated_at=now,
        )


@dataclass
class PortfolioScenarioEvaluation:
    scenario_id: str
    scenario_name: str
    selected_projects: int
    selected_intake_items: int
    total_budget: Decimal
    budget_limit: Decimal | None
    total_capacity_percent: float
    capacity_limit_percent: float | None
    available_capacity_percent: float
    intake_composite_score: int
    over_budget: bool
    over_capacity: bool
    summary: str


@dataclass
class PortfolioScenarioComparison:
    base_scenario_id: str
    base_scenario_name: str
    candidate_scenario_id: str
    candidate_scenario_name: str
    base_evaluation: PortfolioScenarioEvaluation
    candidate_evaluation: PortfolioScenarioEvaluation
    budget_delta: Decimal
    capacity_delta_percent: float
    intake_score_delta: int
    selected_projects_delta: int
    selected_intake_items_delta: int
    added_project_names: list[str] = field(default_factory=list)
    removed_project_names: list[str] = field(default_factory=list)
    added_intake_titles: list[str] = field(default_factory=list)
    removed_intake_titles: list[str] = field(default_factory=list)
    summary: str = ""


__all__ = [
    "PortfolioScenario",
    "PortfolioScenarioComparison",
    "PortfolioScenarioEvaluation",
]
