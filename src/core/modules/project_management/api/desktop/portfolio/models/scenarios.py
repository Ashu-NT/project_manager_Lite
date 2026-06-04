from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioScenarioDesktopDto:
    id: str
    name: str
    budget_limit: float | None
    budget_limit_label: str
    capacity_limit_percent: float | None
    capacity_limit_label: str
    project_ids: tuple[str, ...]
    intake_item_ids: tuple[str, ...]
    notes: str
    created_at_label: str


@dataclass(frozen=True)
class PortfolioScenarioEvaluationDesktopDto:
    scenario_id: str
    scenario_name: str
    summary: str
    selected_projects_label: str
    selected_intake_items_label: str
    total_budget_label: str
    budget_limit_label: str
    total_capacity_label: str
    capacity_limit_label: str
    available_capacity_label: str
    intake_score_label: str
    status_label: str


@dataclass(frozen=True)
class PortfolioScenarioComparisonDesktopDto:
    base_scenario_id: str
    base_scenario_name: str
    candidate_scenario_id: str
    candidate_scenario_name: str
    summary: str
    budget_delta_label: str
    capacity_delta_label: str
    intake_score_delta_label: str
    selected_projects_delta_label: str
    selected_intake_items_delta_label: str
    added_project_names: tuple[str, ...]
    removed_project_names: tuple[str, ...]
    added_intake_titles: tuple[str, ...]
    removed_intake_titles: tuple[str, ...]


__all__ = [
    "PortfolioScenarioComparisonDesktopDto",
    "PortfolioScenarioDesktopDto",
    "PortfolioScenarioEvaluationDesktopDto",
]
