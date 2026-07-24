from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)

_DEFAULT_SCORING_TEMPLATE_NAME = "Balanced PMO"


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


def _validate_portfolio_weight(value: object, *, label: str, code: str) -> int:
    resolved = int(value if value not in (None, "") else 0)
    if resolved < 0 or resolved > 9:
        raise ValidationError(
            f"{label} must be between 0 and 9.",
            code=code,
        )
    return resolved


def _validate_portfolio_score(value: object, *, label: str, code: str) -> int:
    resolved = int(value if value not in (None, "") else 0)
    if resolved < 1 or resolved > 5:
        raise ValidationError(
            f"{label} must be between 1 and 5.",
            code=code,
        )
    return resolved


def _validate_non_negative_float(value: object, *, label: str, code: str) -> float:
    resolved = float(value if value not in (None, "") else 0.0)
    if resolved < 0:
        raise ValidationError(
            f"{label} cannot be negative.",
            code=code,
        )
    return resolved


def _validate_optional_non_negative_float(
    value: object,
    *,
    label: str,
    code: str,
) -> float | None:
    if value in (None, ""):
        return None
    return _validate_non_negative_float(value, label=label, code=code)


def _normalize_identifier_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw_values = [value]
    else:
        try:
            raw_values = list(value)
        except TypeError:
            raw_values = [value]
    normalized = {normalize_optional_text(item) for item in raw_values}
    return sorted(item for item in normalized if item)


def _validate_portfolio_date(value: object, *, message: str, code: str) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, date):
        raise ValidationError(message, code=code)
    return value


def _validate_portfolio_datetime(value: object, *, message: str, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(message, code=code)
    return value


@validated_dataclass
class PortfolioIntakeItem:
    id: str
    title: str
    sponsor_name: str
    organization_id: str = ""
    summary: str = ""
    requested_budget: float = 0.0
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
    def _validate_requested_budget(cls, value: object) -> float:
        return _validate_non_negative_float(
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
        requested_budget: float = 0.0,
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
        return (
            int(self.strategic_score or 0) * int(self.strategic_weight or 0)
            + int(self.value_score or 0) * int(self.value_weight or 0)
            + int(self.urgency_score or 0) * int(self.urgency_weight or 0)
            - (int(self.risk_score or 0) * int(self.risk_weight or 0))
        )


@validated_dataclass
class PortfolioScenario:
    id: str
    name: str
    organization_id: str = ""
    budget_limit: float | None = None
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
    def _validate_budget_limit(cls, value: object) -> float | None:
        return _validate_optional_non_negative_float(
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
        budget_limit: float | None = None,
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


@dataclass
class PortfolioExecutiveRow:
    project_id: str
    project_name: str
    project_status: str
    late_tasks: int
    critical_tasks: int
    peak_utilization_percent: float
    cost_variance: float
    pressure_score: int
    pressure_label: str


@dataclass
class PortfolioRecentAction:
    occurred_at: datetime
    project_name: str
    actor_username: str
    action_label: str
    summary: str


@dataclass
class PortfolioScenarioEvaluation:
    scenario_id: str
    scenario_name: str
    selected_projects: int
    selected_intake_items: int
    total_budget: float
    budget_limit: float | None
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
    budget_delta: float
    capacity_delta_percent: float
    intake_score_delta: int
    selected_projects_delta: int
    selected_intake_items_delta: int
    added_project_names: list[str] = field(default_factory=list)
    removed_project_names: list[str] = field(default_factory=list)
    added_intake_titles: list[str] = field(default_factory=list)
    removed_intake_titles: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class PortfolioProjectDependency:
    id: str
    predecessor_project_id: str
    successor_project_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    summary: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> "PortfolioProjectDependency":
        now = datetime.now(timezone.utc)
        normalized_dependency_type = (
            dependency_type
            if isinstance(dependency_type, DependencyType)
            else DependencyType(str(dependency_type))
        )
        return PortfolioProjectDependency(
            id=generate_id(),
            predecessor_project_id=str(predecessor_project_id or "").strip(),
            successor_project_id=str(successor_project_id or "").strip(),
            dependency_type=normalized_dependency_type,
            summary=(summary or "").strip(),
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


__all__ = [
    "PortfolioIntakeStatus",
    "as_portfolio_intake_status",
    "PortfolioIntakeItem",
    "PortfolioScoringTemplate",
    "PortfolioExecutiveRow",
    "PortfolioRecentAction",
    "PortfolioScenario",
    "PortfolioScenarioEvaluation",
    "PortfolioScenarioComparison",
    "PortfolioProjectDependency",
    "PortfolioProjectDependencyView",
]
