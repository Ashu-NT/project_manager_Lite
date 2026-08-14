from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioMetricViewModel,
    PortfolioOverviewViewModel,
)


def build_overview(
    *,
    intake_total: int,
    scenario_count: int,
    hot_projects: int,
    dependency_count: int,
    active_template,
) -> PortfolioOverviewViewModel:
    return PortfolioOverviewViewModel(
        title="Portfolio",
        subtitle="Portfolio planning, intake scoring, scenario comparison, and cross-project delivery pressure.",
        metrics=(
            PortfolioMetricViewModel(
                label="Intake",
                value=str(intake_total),
                supporting_text="Total ideas in the current PM portfolio.",
            ),
            PortfolioMetricViewModel(
                label="Scenarios",
                value=str(scenario_count),
                supporting_text="Saved what-if portfolios ready for evaluation.",
            ),
            PortfolioMetricViewModel(
                label="Hot projects",
                value=str(hot_projects),
                supporting_text="Projects currently marked with delivery pressure, across the full accessible portfolio.",
            ),
            PortfolioMetricViewModel(
                label="Dependencies",
                value=str(dependency_count),
                supporting_text="Cross-project sequencing links tracked at portfolio level.",
            ),
            PortfolioMetricViewModel(
                label="Active template",
                value=active_template.name if active_template else "None",
                supporting_text=(
                    active_template.weight_summary
                    if active_template
                    else "Create or activate a scoring template."
                ),
            ),
        ),
    )
