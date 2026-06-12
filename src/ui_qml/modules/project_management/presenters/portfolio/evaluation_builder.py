from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioSummaryFieldViewModel,
    PortfolioSummaryViewModel,
)


def build_evaluation_summary(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    scenario_id: str,
) -> PortfolioSummaryViewModel:
    if not scenario_id:
        return PortfolioSummaryViewModel(
            title="Scenario Evaluation",
            empty_state="Select a scenario to review budget, capacity, and intake impact.",
        )
    evaluation = desktop_api.evaluate_scenario(scenario_id)
    return PortfolioSummaryViewModel(
        title=f"Scenario Evaluation: {evaluation.scenario_name}",
        subtitle=evaluation.summary,
        fields=(
            PortfolioSummaryFieldViewModel(
                label="Projects",
                value=evaluation.selected_projects_label,
            ),
            PortfolioSummaryFieldViewModel(
                label="Intake items",
                value=evaluation.selected_intake_items_label,
            ),
            PortfolioSummaryFieldViewModel(
                label="Budget",
                value=evaluation.total_budget_label,
                supporting_text=f"Limit: {evaluation.budget_limit_label}",
            ),
            PortfolioSummaryFieldViewModel(
                label="Capacity",
                value=evaluation.total_capacity_label,
                supporting_text=f"Limit: {evaluation.capacity_limit_label}",
            ),
            PortfolioSummaryFieldViewModel(
                label="Available capacity",
                value=evaluation.available_capacity_label,
            ),
            PortfolioSummaryFieldViewModel(
                label="Intake score",
                value=evaluation.intake_score_label,
                supporting_text=evaluation.status_label,
            ),
        ),
    )
