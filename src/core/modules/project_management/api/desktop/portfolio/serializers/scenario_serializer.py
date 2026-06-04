from src.core.modules.project_management.api.desktop.portfolio.models.scenarios import (
    PortfolioScenarioComparisonDesktopDto,
    PortfolioScenarioDesktopDto,
    PortfolioScenarioEvaluationDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.formatters.money_formatter import (
    format_money,
    format_signed_money,
)
from src.core.modules.project_management.api.desktop.portfolio.formatters.percent_formatter import (
    format_percent,
    format_signed_int,
    format_signed_percent,
)
from src.core.modules.project_management.api.desktop.portfolio.formatters.date_formatter import format_datetime


def serialize_scenario(scenario) -> PortfolioScenarioDesktopDto:
    return PortfolioScenarioDesktopDto(
        id=scenario.id,
        name=scenario.name,
        budget_limit=scenario.budget_limit,
        budget_limit_label=format_money(scenario.budget_limit, fallback="No budget limit"),
        capacity_limit_percent=scenario.capacity_limit_percent,
        capacity_limit_label=format_percent(scenario.capacity_limit_percent, fallback="No capacity limit"),
        project_ids=tuple(scenario.project_ids or ()),
        intake_item_ids=tuple(scenario.intake_item_ids or ()),
        notes=scenario.notes or "",
        created_at_label=format_datetime(scenario.created_at),
    )


def serialize_evaluation(evaluation) -> PortfolioScenarioEvaluationDesktopDto:
    status_parts: list[str] = []
    if evaluation.over_budget:
        status_parts.append("Over budget")
    if evaluation.over_capacity:
        status_parts.append("Over capacity")
    if not status_parts:
        status_parts.append("Within limits")
    return PortfolioScenarioEvaluationDesktopDto(
        scenario_id=evaluation.scenario_id,
        scenario_name=evaluation.scenario_name,
        summary=evaluation.summary,
        selected_projects_label=str(int(evaluation.selected_projects or 0)),
        selected_intake_items_label=str(int(evaluation.selected_intake_items or 0)),
        total_budget_label=format_money(evaluation.total_budget),
        budget_limit_label=format_money(evaluation.budget_limit, fallback="No budget limit"),
        total_capacity_label=format_percent(evaluation.total_capacity_percent),
        capacity_limit_label=format_percent(evaluation.capacity_limit_percent, fallback="No capacity limit"),
        available_capacity_label=format_percent(evaluation.available_capacity_percent),
        intake_score_label=str(int(evaluation.intake_composite_score or 0)),
        status_label=" | ".join(status_parts),
    )


def serialize_comparison(comparison) -> PortfolioScenarioComparisonDesktopDto:
    return PortfolioScenarioComparisonDesktopDto(
        base_scenario_id=comparison.base_scenario_id,
        base_scenario_name=comparison.base_scenario_name,
        candidate_scenario_id=comparison.candidate_scenario_id,
        candidate_scenario_name=comparison.candidate_scenario_name,
        summary=comparison.summary,
        budget_delta_label=format_signed_money(comparison.budget_delta),
        capacity_delta_label=format_signed_percent(comparison.capacity_delta_percent),
        intake_score_delta_label=format_signed_int(comparison.intake_score_delta),
        selected_projects_delta_label=format_signed_int(comparison.selected_projects_delta),
        selected_intake_items_delta_label=format_signed_int(comparison.selected_intake_items_delta),
        added_project_names=tuple(comparison.added_project_names or ()),
        removed_project_names=tuple(comparison.removed_project_names or ()),
        added_intake_titles=tuple(comparison.added_intake_titles or ()),
        removed_intake_titles=tuple(comparison.removed_intake_titles or ()),
    )


__all__ = ["serialize_comparison", "serialize_evaluation", "serialize_scenario"]
