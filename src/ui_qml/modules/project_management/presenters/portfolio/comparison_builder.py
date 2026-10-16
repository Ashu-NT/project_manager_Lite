from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_signed_money,
)
from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_signed_int,
    format_signed_percent,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioSummaryFieldViewModel,
    PortfolioSummaryViewModel,
)


def build_comparison_summary(
    desktop_api: ProjectManagementPortfolioDesktopApi,
    *,
    base_scenario_id: str,
    compare_scenario_id: str,
) -> PortfolioSummaryViewModel:
    if not base_scenario_id or not compare_scenario_id:
        return PortfolioSummaryViewModel(
            title="Scenario Comparison",
            empty_state="Select two saved scenarios to compare budget, capacity, and selection changes.",
        )
    comparison = desktop_api.compare_scenarios(base_scenario_id, compare_scenario_id)
    added_projects = ", ".join(comparison.added_project_names) or "None"
    removed_projects = ", ".join(comparison.removed_project_names) or "None"
    added_intake = ", ".join(comparison.added_intake_titles) or "None"
    removed_intake = ", ".join(comparison.removed_intake_titles) or "None"
    return PortfolioSummaryViewModel(
        title=(
            f"Scenario Comparison: {comparison.base_scenario_name} vs "
            f"{comparison.candidate_scenario_name}"
        ),
        subtitle=comparison.summary,
        fields=(
            PortfolioSummaryFieldViewModel(
                label="Budget delta",
                value=format_signed_money(comparison.budget_delta),
            ),
            PortfolioSummaryFieldViewModel(
                label="Capacity delta",
                value=format_signed_percent(comparison.capacity_delta_percent),
            ),
            PortfolioSummaryFieldViewModel(
                label="Projects delta",
                value=format_signed_int(comparison.selected_projects_delta),
                supporting_text=f"Added: {added_projects} | Removed: {removed_projects}",
            ),
            PortfolioSummaryFieldViewModel(
                label="Intake delta",
                value=format_signed_int(comparison.selected_intake_items_delta),
                supporting_text=f"Added: {added_intake} | Removed: {removed_intake}",
            ),
            PortfolioSummaryFieldViewModel(
                label="Score delta",
                value=format_signed_int(comparison.intake_score_delta),
            ),
        ),
    )
