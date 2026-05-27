from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.identifiers import generate_id


class PortfolioIntakeStatus(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"


@dataclass
class PortfolioIntakeItem:
    id: str
    title: str
    sponsor_name: str
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

    @staticmethod
    def create(
        *,
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
            title=(title or "").strip(),
            sponsor_name=(sponsor_name or "").strip(),
            summary=(summary or "").strip(),
            requested_budget=float(requested_budget or 0.0),
            requested_capacity_percent=float(requested_capacity_percent or 0.0),
            target_start_date=target_start_date,
            strategic_score=int(strategic_score or 0),
            value_score=int(value_score or 0),
            urgency_score=int(urgency_score or 0),
            risk_score=int(risk_score or 0),
            scoring_template_id=str(scoring_template_id or "").strip(),
            scoring_template_name=(scoring_template_name or "Balanced PMO").strip() or "Balanced PMO",
            strategic_weight=int(strategic_weight or 0),
            value_weight=int(value_weight or 0),
            urgency_weight=int(urgency_weight or 0),
            risk_weight=int(risk_weight or 0),
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


@dataclass
class PortfolioScenario:
    id: str
    name: str
    budget_limit: float | None = None
    capacity_limit_percent: float | None = None
    project_ids: list[str] = field(default_factory=list)
    intake_item_ids: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
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
            name=(name or "").strip(),
            budget_limit=(None if budget_limit is None else float(budget_limit)),
            capacity_limit_percent=(
                None if capacity_limit_percent is None else float(capacity_limit_percent)
            ),
            project_ids=sorted({str(item).strip() for item in (project_ids or []) if str(item).strip()}),
            intake_item_ids=sorted(
                {str(item).strip() for item in (intake_item_ids or []) if str(item).strip()}
            ),
            notes=(notes or "").strip(),
            created_at=now,
            updated_at=now,
        )


@dataclass
class PortfolioScoringTemplate:
    id: str
    name: str
    summary: str = ""
    strategic_weight: int = 3
    value_weight: int = 2
    urgency_weight: int = 2
    risk_weight: int = 1
    is_active: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
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
            name=(name or "").strip(),
            summary=(summary or "").strip(),
            strategic_weight=int(strategic_weight or 0),
            value_weight=int(value_weight or 0),
            urgency_weight=int(urgency_weight or 0),
            risk_weight=int(risk_weight or 0),
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
