from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_percent,
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
                value=str(evaluation.selected_projects),
            ),
            PortfolioSummaryFieldViewModel(
                label="Intake items",
                value=str(evaluation.selected_intake_items),
            ),
            PortfolioSummaryFieldViewModel(
                label="Budget",
                value=format_money(evaluation.total_budget),
                supporting_text=f"Limit: {format_money(evaluation.budget_limit, fallback="No budget limit")}",
            ),
            PortfolioSummaryFieldViewModel(
                label="Capacity",
                value=format_percent(evaluation.total_capacity_percent),
                supporting_text=f"Limit: {format_percent(evaluation.capacity_limit_percent, fallback="No capacity limit")}",
            ),
            PortfolioSummaryFieldViewModel(
                label="Available capacity",
                value=format_percent(evaluation.available_capacity_percent),
            ),
            PortfolioSummaryFieldViewModel(
                label="Intake score",
                value=str(evaluation.intake_composite_score),
                supporting_text=" | ".join(label for flag, label in ((evaluation.over_budget, "Over budget"), (evaluation.over_capacity, "Over capacity")) if flag) or "Within limits",
            ),
        ),
    )
