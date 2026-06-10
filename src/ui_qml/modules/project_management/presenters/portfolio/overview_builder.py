from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioMetricViewModel,
    PortfolioOverviewViewModel,
)


def build_overview(
    *,
    filtered_intake_items,
    intake_items,
    scenarios,
    hot_projects: int,
    dependencies,
    active_template,
) -> PortfolioOverviewViewModel:
    return PortfolioOverviewViewModel(
        title="Portfolio",
        subtitle="Portfolio planning, intake scoring, scenario comparison, and cross-project delivery pressure.",
        metrics=(
            PortfolioMetricViewModel(
                label="Intake",
                value=str(len(filtered_intake_items)),
                supporting_text=f"{len(intake_items)} total ideas in the current PM portfolio.",
            ),
            PortfolioMetricViewModel(
                label="Scenarios",
                value=str(len(scenarios)),
                supporting_text="Saved what-if portfolios ready for evaluation.",
            ),
            PortfolioMetricViewModel(
                label="Hot projects",
                value=str(hot_projects),
                supporting_text="Projects currently marked with delivery pressure.",
            ),
            PortfolioMetricViewModel(
                label="Dependencies",
                value=str(len(dependencies)),
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
