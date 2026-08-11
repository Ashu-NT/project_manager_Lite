from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsMetricViewModel,
    FinancialsOverviewViewModel,
)

def build_overview(
    *,
    project_options: Any,
    selected_project_id: str,
    snapshot: Any,
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
                supporting_text="Current approved budget authorization.",
            ),
            FinancialsMetricViewModel(
                label="Planned",
                value=snapshot.planned_label,
                supporting_text="Current versioned planned-cost snapshot.",
            ),
            FinancialsMetricViewModel(
                label="Open commitments",
                value=snapshot.committed_label,
                supporting_text="Unmatched Procurement commitment balance.",
            ),
            FinancialsMetricViewModel(
                label="Actual",
                value=snapshot.actual_label,
                supporting_text="Net posted actuals, including reversal entries.",
            ),
            FinancialsMetricViewModel(
                label="Available",
                value=snapshot.available_label,
                supporting_text="Approved budget less posted actuals and open commitments.",
            ),
        ),
    )
