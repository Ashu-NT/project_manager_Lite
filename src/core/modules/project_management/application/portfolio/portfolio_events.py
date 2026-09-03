from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PortfolioIntakeItemChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioIntakeItemChanged:

    tenant_id: str
    organization_id: str
    intake_item_id: str
    change_type: PortfolioIntakeItemChangeType
    occurred_at: datetime


class PortfolioScenarioChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioScenarioChanged:
    """`create_scenario`/`update_scenario` -- no delete/remove command exists in source."""

    tenant_id: str
    organization_id: str
    scenario_id: str
    change_type: PortfolioScenarioChangeType
    occurred_at: datetime


class PortfolioScoringTemplateChangeType(str, Enum):
    CREATED = "CREATED"
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioScoringTemplateChanged:

    tenant_id: str
    organization_id: str
    scoring_template_id: str
    change_type: PortfolioScoringTemplateChangeType
    occurred_at: datetime


class PortfolioProjectDependencyChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioProjectDependencyChanged:
    """`create_project_dependency`/`remove_project_dependency` -- the dependency row itself is
    immutable once created (no update command exists), so only ADDED/REMOVED are real facts."""

    tenant_id: str
    organization_id: str
    dependency_id: str
    predecessor_project_id: str
    successor_project_id: str
    change_type: PortfolioProjectDependencyChangeType
    occurred_at: datetime


__all__ = [
    "PortfolioIntakeItemChangeType",
    "PortfolioIntakeItemChanged",
    "PortfolioScenarioChangeType",
    "PortfolioScenarioChanged",
    "PortfolioScoringTemplateChangeType",
    "PortfolioScoringTemplateChanged",
    "PortfolioProjectDependencyChangeType",
    "PortfolioProjectDependencyChanged",
]
