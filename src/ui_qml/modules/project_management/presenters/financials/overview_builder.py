from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsMetricViewModel,
    FinancialsOverviewViewModel,
)


def build_overview(
    *,
    project_options,
    selected_project_id: str,
    snapshot,
    all_costs,
    filtered_costs,
) -> FinancialsOverviewViewModel:
    project_label = next(
        (option.label for option in project_options if option.value == selected_project_id),
        "Financials",
    )
    return FinancialsOverviewViewModel(
        title="Financials",
        subtitle=(
            f"{project_label} cost control, budget health, ledger, and cashflow."
            if selected_project_id
            else "Select a project to review cost control and finance exposure."
        ),
        metrics=(
            FinancialsMetricViewModel(
                label="Budget",
                value=snapshot.budget_label,
                supporting_text="Planned budget available to the selected project.",
            ),
            FinancialsMetricViewModel(
                label="Planned",
                value=snapshot.planned_label,
                supporting_text=f"{len(all_costs)} cost items loaded; {len(filtered_costs)} shown.",
            ),
            FinancialsMetricViewModel(
                label="Committed",
                value=snapshot.committed_label,
                supporting_text="Committed exposure recorded on the selected project.",
            ),
            FinancialsMetricViewModel(
                label="Actual",
                value=snapshot.actual_label,
                supporting_text="Actual spend captured in the project ledger.",
            ),
            FinancialsMetricViewModel(
                label="Available",
                value=snapshot.available_label,
                supporting_text="Remaining headroom after current exposure.",
            ),
        ),
    )
