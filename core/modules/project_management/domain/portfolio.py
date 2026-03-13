from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Iterable

from core.modules.project_management.domain.identifiers import generate_id


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
            status=status,
            created_at=now,
            updated_at=now,
            version=1,
        )

    @property
    def composite_score(self) -> int:
        return (
            int(self.strategic_score or 0) * 3
            + int(self.value_score or 0) * 2
            + int(self.urgency_score or 0) * 2
            - int(self.risk_score or 0)
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


__all__ = [
    "PortfolioIntakeStatus",
    "PortfolioIntakeItem",
    "PortfolioScenario",
    "PortfolioScenarioEvaluation",
]
